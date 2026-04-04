"""Heartbeat service - periodic agent wake-up to check for tasks."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Coroutine

from loguru import logger
if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider

_HEARTBEAT_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "heartbeat",
            "description": "Report heartbeat decision after reviewing tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["skip", "run"],
                        "description": "skip = nothing to do, run = has active tasks",
                    },
                    "tasks": {
                        "type": "string",
                        "description": "Natural-language summary of active tasks (required for run)",
                    },
                },
                "required": ["action"],
            },
        },
    }
]


class HeartbeatService:
    """
    Periodic heartbeat service that wakes the agent to check for tasks.

    Phase 1 (decision): reads HEARTBEAT.md and asks the LLM — via a virtual
    tool call — whether there are active tasks.  This avoids free-text parsing
    and the unreliable HEARTBEAT_OK token.

    Phase 2 (execution): only triggered when Phase 1 returns ``run``.  The
    ``on_execute`` callback runs the task through the full agent loop and
    returns the result to deliver.
    
    Subagent Heartbeats: Optional per-subagent heartbeat tasks that run
    in parallel to the main heartbeat.
    """

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        on_execute: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        on_notify: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        on_documente: Callable[[str, str], Coroutine[Any, Any, None]] | None = None,
        interval_s: int = 30 * 60,
        enabled: bool = True,
        timezone: str | None = None,
        subagent_callbacks: dict[str, Callable[[str], Coroutine[Any, Any, str]]] | None = None,
    ):
        self.workspace = workspace
        self.provider = provider
        self.model = model
        self.on_execute = on_execute
        self.on_notify = on_notify
        self.on_documente = on_documente
        self.interval_s = interval_s
        self.enabled = enabled
        self.timezone = timezone
        self.subagent_callbacks = subagent_callbacks or {}
        self._running = False
        self._task: asyncio.Task | None = None
        self._subagent_tasks: dict[str, asyncio.Task] = {}
        self._subagent_intervals: dict[str, int] = {}
        self._subagent_last_run: dict[str, float] = {}

    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / "HEARTBEAT.md"

    def _read_heartbeat_file(self) -> str | None:
        if self.heartbeat_file.exists():
            try:
                return self.heartbeat_file.read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    async def _decide(self, content: str) -> tuple[str, str]:
        """Phase 1: ask LLM to decide skip/run via virtual tool call.

        Returns (action, tasks) where action is 'skip' or 'run'.
        """
        from nanobot.utils.helpers import current_time_str

        response = await self.provider.chat_with_retry(
            messages=[
                {"role": "system", "content": (
                    "You are a heartbeat agent. Call the heartbeat tool to report your decision.\n\n"
                    "CRITICAL RULES:\n"
                    "1. BEFORE marking ANY task as [x], verify you actually performed the work\n"
                    "2. If task was already marked [x] TODAY → SKIP (no duplicate completions)\n"
                    "3. Only [x] if NEW work, NEW results, NEW file modifications\n"
                    "4. Without evidence (file path) → keep as [ ] (not complete)"
                )},
                {"role": "user", "content": (
                    f"Current Time: {current_time_str(self.timezone)}\n\n"
                    "Review the following HEARTBEAT.md and decide whether there are active tasks.\n\n"
                    f"{content}"
                )},
            ],
            tools=_HEARTBEAT_TOOL,
            model=self.model,
        )

        if not response.has_tool_calls:
            return "skip", ""

        args = response.tool_calls[0].arguments
        return args.get("action", "skip"), args.get("tasks", "")

    async def start(self) -> None:
        """Start the heartbeat service."""
        if not self.enabled:
            logger.info("Heartbeat disabled")
            return
        if self._running:
            logger.warning("Heartbeat already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Heartbeat started (every {}s)", self.interval_s)

    def stop(self) -> None:
        """Stop the heartbeat service."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    async def _run_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            try:
                await asyncio.sleep(self.interval_s)
                if self._running:
                    await self._tick()
                    # Also run subagent heartbeats
                    if self.subagent_callbacks:
                        await self._run_subagent_heartbeats()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Heartbeat error: {}", e)

    async def _tick(self) -> None:
        """Execute a single heartbeat tick."""
        from nanobot.utils.evaluator import evaluate_response

        content = self._read_heartbeat_file()
        if not content:
            logger.debug("Heartbeat: HEARTBEAT.md missing or empty")
            return

        logger.info("Heartbeat: checking for tasks...")

        try:
            action, tasks = await self._decide(content)

            if action != "run":
                logger.info("Heartbeat: OK (nothing to report)")
                return

            logger.info("Heartbeat: tasks found, executing...")
            if self.on_execute:
                response = await self.on_execute(tasks)

                if response:
                    should_notify = await evaluate_response(
                        response, tasks, self.provider, self.model,
                    )
                    if should_notify and self.on_notify:
                        logger.info("Heartbeat: completed, delivering response")
                        await self.on_notify(response)
                    else:
                        logger.info("Heartbeat: silenced by post-run evaluation")
                    
                    if self.on_documente:
                        asyncio.create_task(self._documente_async(tasks, response))
        except Exception:
            logger.exception("Heartbeat execution failed")

    async def _documente_async(self, tasks: str, response: str) -> None:
        """Async documentation of heartbeat tasks and results."""
        try:
            if self.on_documente:
                await self.on_documente(tasks, response)
        except Exception:
            logger.exception("Heartbeat documentation failed")

    async def trigger_now(self) -> str | None:
        """Manually trigger a heartbeat."""
        content = self._read_heartbeat_file()
        if not content:
            return None
        action, tasks = await self._decide(content)
        if action != "run" or not self.on_execute:
            return None
        return await self.on_execute(tasks)

    def load_subagent_configs(self) -> dict[str, dict]:
        """Load subagent configurations from .subagents directory."""
        subagent_dir = self.workspace / ".subagents"
        configs = {}
        
        if not subagent_dir.exists():
            return configs
        
        # Load main config
        config_file = subagent_dir / "config.json"
        if config_file.exists():
            try:
                main_config = json.loads(config_file.read_text(encoding="utf-8"))
                group_chat = main_config.get("group_chat", "")
            except json.JSONDecodeError:
                group_chat = ""
        else:
            group_chat = ""
        
        # Load individual subagent configs
        for config_file in subagent_dir.glob("*.json"):
            if config_file.name == "config.json":
                continue
            try:
                subagent_config = json.loads(config_file.read_text(encoding="utf-8"))
                subagent_id = config_file.stem
                
                # Check if subagent has heartbeat enabled
                heartbeat_config = subagent_config.get("heartbeat", {})
                if heartbeat_config.get("enabled", False):
                    configs[subagent_id] = {
                        "role": subagent_config.get("role", subagent_id),
                        "task": heartbeat_config.get("task", ""),
                        "interval_s": heartbeat_config.get("interval_s", 1800),
                        "allowed_chats": subagent_config.get("allowed_chats", [group_chat]),
                    }
            except json.JSONDecodeError:
                continue
        
        return configs

    def register_subagent_callback(self, subagent_id: str, callback: Callable[[str], Coroutine[Any, Any, str]]) -> None:
        """Register a callback function for a subagent's heartbeat."""
        self.subagent_callbacks[subagent_id] = callback

    async def trigger_subagent_heartbeat(self, subagent_id: str, task: str) -> str | None:
        """Trigger a specific subagent's heartbeat task."""
        callback = self.subagent_callbacks.get(subagent_id)
        if callback:
            return await callback(task)
        return None

    async def _run_subagent_heartbeats(self) -> None:
        """Run all enabled subagent heartbeats based on their intervals."""
        import time
        current_time = time.time()
        
        configs = self.load_subagent_configs()
        
        for subagent_id, config in configs.items():
            interval = config.get("interval_s", 1800)
            last_run = self._subagent_last_run.get(subagent_id, 0)
            
            # Check if enough time has passed
            if current_time - last_run >= interval:
                logger.info("Subagent heartbeat [{}]: checking tasks...", subagent_id)
                self._subagent_last_run[subagent_id] = current_time
                
                task = config.get("task", "")
                if task and subagent_id in self.subagent_callbacks:
                    try:
                        response = await self.trigger_subagent_heartbeat(subagent_id, task)
                        if response:
                            logger.info("Subagent [{}] heartbeat completed", subagent_id)
                    except Exception:
                        logger.exception("Subagent [{}] heartbeat failed", subagent_id)
