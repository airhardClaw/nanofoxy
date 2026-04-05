"""Memory consolidation logic."""

from __future__ import annotations

import asyncio
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session, SessionManager
    from nanobot.agent.memory.store import MemoryStore
    from nanobot.agent.memory.qmd_engine import QMDEngine

from nanobot.utils.helpers import estimate_message_tokens, estimate_prompt_tokens_chain


class MemoryConsolidator:
    """Owns consolidation policy, locking, and session offset updates."""

    _MAX_CONSOLIDATION_ROUNDS = 3  # Reduced from 5 for faster 8B
    _SAFETY_BUFFER = 512  # Reduced from 1024 for 8B efficiency

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        sessions: SessionManager,
        context_window_tokens: int,
        build_messages: Callable[..., list[dict[str, Any]]],
        get_tool_definitions: Callable[[], list[dict[str, Any]]],
        max_completion_tokens: int = 4096,  # Reduced from 4096 for 8B
        qmd_engine: QMDEngine | None = None,
        dreaming_config: dict[str, Any] | None = None,
    ):
        from nanobot.agent.memory import MemoryStore, DreamingService

        self.store = MemoryStore(workspace)
        self.qmd_engine = qmd_engine
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.context_window_tokens = context_window_tokens
        self.max_completion_tokens = max_completion_tokens
        self._build_messages = build_messages
        self._get_tool_definitions = get_tool_definitions
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

        if dreaming_config and dreaming_config.get("enabled", True):
            self.dreaming = DreamingService(
                workspace=workspace,
                provider=provider,
                model=model,
                config=dreaming_config,
            )
        else:
            self.dreaming = None

    def get_lock(self, session_key: str) -> asyncio.Lock:
        """Return the shared consolidation lock for one session."""
        return self._locks.setdefault(session_key, asyncio.Lock())

    async def consolidate_messages(self, messages: list[dict[str, object]]) -> bool:
        """Archive a selected message chunk into persistent memory."""
        success = await self.store.consolidate(messages, self.provider, self.model)
        
        if success and self.qmd_engine:
            await self._index_to_qmd(messages)
        
        return success

    async def _index_to_qmd(self, messages: list[dict[str, object]]) -> None:
        """Index consolidated messages to QMD if session indexing is enabled."""
        if not self.qmd_engine or not self.qmd_engine.sessions_enabled:
            return
        
        try:
            await self.qmd_engine.index_messages(messages)
        except Exception:
            logger.exception("Failed to index messages to QMD")

    def pick_consolidation_boundary(
        self,
        session: Session,
        tokens_to_remove: int,
    ) -> tuple[int, int] | None:
        """Pick a user-turn boundary that removes enough old prompt tokens."""
        start = session.last_consolidated
        if start >= len(session.messages) or tokens_to_remove <= 0:
            return None

        removed_tokens = 0
        last_boundary: tuple[int, int] | None = None
        for idx in range(start, len(session.messages)):
            message = session.messages[idx]
            if idx > start and message.get("role") == "user":
                last_boundary = (idx, removed_tokens)
                if removed_tokens >= tokens_to_remove:
                    return last_boundary
            removed_tokens += estimate_message_tokens(message)

        return last_boundary

    def estimate_session_prompt_tokens(self, session: Session) -> tuple[int, str]:
        """Estimate current prompt size for the normal session history view."""
        history = session.get_history(max_messages=0)
        channel, chat_id = (session.key.split(":", 1) if ":" in session.key else (None, None))
        probe_messages = self._build_messages(
            history=history,
            current_message="[token-probe]",
            channel=channel,
            chat_id=chat_id,
        )
        return estimate_prompt_tokens_chain(
            self.provider,
            self.model,
            probe_messages,
            self._get_tool_definitions(),
        )

    async def archive_messages(self, messages: list[dict[str, object]]) -> bool:
        """Archive messages with guaranteed persistence (retries until raw-dump fallback)."""
        if not messages:
            return True
        for _ in range(self.store._MAX_FAILURES_BEFORE_RAW_ARCHIVE):
            if await self.consolidate_messages(messages):
                return True
        return True

    async def maybe_consolidate_by_tokens(self, session: Session) -> None:
        """Loop: archive old messages until prompt fits within safe budget.

        The budget reserves space for completion tokens and a safety buffer
        so the LLM request never exceeds the context window.
        """
        if not session.messages or self.context_window_tokens <= 0:
            return

        lock = self.get_lock(session.key)
        async with lock:
            budget = self.context_window_tokens - self.max_completion_tokens - self._SAFETY_BUFFER
            target = budget // 2
            estimated, source = self.estimate_session_prompt_tokens(session)
            if estimated <= 0:
                return
            if estimated < budget:
                logger.debug(
                    "Token consolidation idle {}: {}/{} via {}",
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                )
                return

            for round_num in range(self._MAX_CONSOLIDATION_ROUNDS):
                if estimated <= target:
                    return

                boundary = self.pick_consolidation_boundary(session, max(1, estimated - target))
                if boundary is None:
                    logger.debug(
                        "Token consolidation: no safe boundary for {} (round {})",
                        session.key,
                        round_num,
                    )
                    return

                end_idx = boundary[0]
                chunk = session.messages[session.last_consolidated:end_idx]
                if not chunk:
                    return

                logger.info(
                    "Token consolidation round {} for {}: {}/{} via {}, chunk={} msgs",
                    round_num,
                    session.key,
                    estimated,
                    self.context_window_tokens,
                    source,
                    len(chunk),
                )
                if not await self.consolidate_messages(chunk):
                    return
                session.last_consolidated = end_idx
                self.sessions.save(session)

                estimated, source = self.estimate_session_prompt_tokens(session)
                if estimated <= 0:
                    return

    PRE_CONSOLIDATE_THRESHOLD = 0.6  # Lower = trigger earlier for larger 8B context

    async def pre_consolidate_if_needed(
        self,
        session: Session,
    ) -> bool:
        """Proactively consolidate messages BEFORE sending to LLM.
        
        Called when context usage exceeds threshold to prevent context window errors.
        Returns True if consolidation was performed or not needed.
        """
        if not session.messages or self.context_window_tokens <= 0:
            return True

        lock = self.get_lock(session.key)
        async with lock:
            budget = self.context_window_tokens - self.max_completion_tokens - self._SAFETY_BUFFER
            threshold = int(budget * self.PRE_CONSOLIDATE_THRESHOLD)
            
            estimated, source = self.estimate_session_prompt_tokens(session)
            if estimated <= 0:
                return True
            
            if estimated < threshold:
                return True
            
            logger.info(
                "Pre-consolidation for {}: {}/{} (threshold {})",
                session.key,
                estimated,
                self.context_window_tokens,
                threshold,
            )
            
            target = int(budget * 0.5)
            for round_num in range(self._MAX_CONSOLIDATION_ROUNDS):
                if estimated <= target:
                    break

                boundary = self.pick_consolidation_boundary(session, max(1, estimated - target))
                if boundary is None:
                    break

                end_idx = boundary[0]
                chunk = session.messages[session.last_consolidated:end_idx]
                if not chunk:
                    break

                logger.info(
                    "Pre-consolidation round {} for {}: archiving {} msgs",
                    round_num,
                    session.key,
                    len(chunk),
                )
                if not await self.consolidate_messages(chunk):
                    break
                session.last_consolidated = end_idx
                self.sessions.save(session)

                estimated, source = self.estimate_session_prompt_tokens(session)
                if estimated <= 0:
                    break

            logger.info(
                "Pre-consolidation done for {}: {}/{}",
                session.key,
                estimated,
                self.context_window_tokens,
            )
            return True

    async def run_dreaming(self, phase: str | None = None) -> dict[str, int]:
        """Run dreaming phases. If phase is specified, run only that phase."""
        if not self.dreaming:
            return {"light": 0, "deep": 0, "rem": 0}

        results = {}
        if phase is None or phase == "light":
            results["light"] = await self.dreaming.run_light_phase()
        if phase is None or phase == "deep":
            results["deep"] = await self.dreaming.run_deep_phase()
        if phase is None or phase == "rem":
            results["rem"] = await self.dreaming.run_rem_phase()

        return results

    def get_dreaming_stats(self) -> dict[str, Any]:
        """Get dreaming statistics."""
        if not self.dreaming:
            return {"enabled": False}
        return self.dreaming.get_stats()