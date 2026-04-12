"""QMD memory engine - combines BM25, vector search, and reranking."""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir


class QMDEngine:
    """QMD sidecar for enhanced memory search with BM25, vector search, and reranking."""

    DEFAULT_COLLECTION = "workspace"
    SESSIONS_COLLECTION = "sessions"

    def __init__(
        self,
        workspace: Path,
        agent_id: str,
        config: dict[str, Any] | None = None,
    ):
        self.workspace = workspace
        self.agent_id = agent_id
        self.config = config or {}

        self.qmd_home = ensure_dir(Path.home() / ".nanofoxy" / "agents" / agent_id / "qmd")
        self.collections_dir = ensure_dir(self.qmd_home / "collections")

        self.paths = self.config.get("paths", [])
        self.sessions_enabled = self.config.get("sessions", {}).get("enabled", True)
        self.update_interval = self.config.get("updateIntervalSeconds", 300)
        self.timeout_ms = self.config.get("limits", {}).get("timeoutMs", 4000)

        self._qmd_available: bool | None = None
        self._update_task: asyncio.Task | None = None

    @property
    def qmd_available(self) -> bool:
        """Check if qmd binary is available on PATH."""
        if self._qmd_available is None:
            self._qmd_available = shutil.which("qmd") is not None
        return self._qmd_available

    async def ensure_available(self) -> bool:
        """Ensure QMD is available, return False if not."""
        if not self.qmd_available:
            logger.warning(
                "QMD not found on PATH. Install with: bun install -g @tobilu/qmd"
            )
            return False
        return True

    async def initialize(self) -> bool:
        """Initialize QMD collections and start periodic updates."""
        if not await self.ensure_available():
            return False

        try:
            await self._create_collections()
            await self._index_workspace()

            for path_config in self.paths:
                await self._index_extra_path(path_config)

            self._start_periodic_updates()

            logger.info("QMD initialized at {}", self.qmd_home)
            return True
        except Exception:
            logger.exception("Failed to initialize QMD")
            return False

    async def _create_collections(self) -> None:
        """Create QMD collections for workspace and sessions."""
        await self._run_qmd("create", self.DEFAULT_COLLECTION)
        if self.sessions_enabled:
            await self._run_qmd("create", self.SESSIONS_COLLECTION)

    async def _index_workspace(self) -> None:
        """Index the workspace memory files."""
        memory_dir = self.workspace / "memory"
        if not memory_dir.exists():
            return

        files = []
        for ext in ("*.md", "*.txt"):
            files.extend(memory_dir.glob(ext))

        for file in files:
            await self._add_to_collection(self.DEFAULT_COLLECTION, file)

    async def _index_extra_path(self, path_config: dict[str, Any]) -> None:
        """Index an extra path with pattern."""
        name = path_config.get("name", "extra")
        path = Path(path_config.get("path", "").replace("~", str(Path.home())))
        pattern = path_config.get("pattern", "**/*")

        if not path.exists():
            logger.warning("QMD extra path does not exist: {}", path)
            return

        collection_path = ensure_dir(self.collections_dir / name)

        for file in path.glob(pattern):
            if file.is_file():
                dest = collection_path / file.relative_to(path)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, dest)

        await self._run_qmd("create", name)
        await self._run_qmd("update", name)

    async def index_messages(self, messages: list[dict[str, Any]]) -> None:
        """Index session messages to sessions collection."""
        if not self.sessions_enabled or not messages:
            return

        sessions_dir = ensure_dir(self.collections_dir / self.SESSIONS_COLLECTION)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = sessions_dir / f"session_{timestamp}.md"

        content = self._format_messages_for_indexing(messages)
        session_file.write_text(content, encoding="utf-8")

        await self._run_qmd("update", self.SESSIONS_COLLECTION)

    def _format_messages_for_indexing(self, messages: list[dict[str, Any]]) -> str:
        """Format messages for QMD indexing (sanitized User/Assistant turns)."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if not content:
                continue

            ts = msg.get("timestamp", "?")[:16]
            lines.append(f"[{ts}] {role.upper()}: {content}")

        return "\n\n".join(lines)

    async def search(
        self,
        query: str,
        collection: str | None = None,
        mode: str = "search",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search using QMD with specified mode.

        Modes: search (BM25), vsearch (vector), query (BM25 + reranking)
        """
        if not await self.ensure_available():
            return []

        coll = collection or self.DEFAULT_COLLECTION

        try:
            result = await self._run_qmd(
                mode,
                coll,
                "--query", query,
                "--limit", str(limit),
                "--timeout", str(self.timeout_ms),
            )

            return self._parse_search_results(result, coll)
        except Exception:
            logger.exception("QMD search failed for query: {}", query)
            return []

    def _parse_search_results(self, output: str, collection: str) -> list[dict[str, Any]]:
        """Parse QMD search output into structured results."""
        results = []
        lines = output.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("qmd/"):
                parts = line.split(":", 1)
                if len(parts) >= 2:
                    path = parts[0]
                    snippet = parts[1].strip()
                    results.append({
                        "collection": collection,
                        "path": path,
                        "snippet": snippet,
                        "source": f"{path}",
                    })
            else:
                results.append({
                    "collection": collection,
                    "content": line,
                })

        return results

    async def _run_qmd(self, *args: str) -> str:
        """Run qmd command and return output."""
        cmd = ["qmd", *args]

        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.qmd_home),
                ),
                timeout=self.timeout_ms / 1000,
            )
            stdout, stderr = await result.communicate()

            if result.returncode != 0:
                logger.warning("QMD command failed: {} -> {}", cmd, stderr.decode())
                return ""

            return stdout.decode("utf-8")
        except asyncio.TimeoutError:
            logger.warning("QMD command timed out: {}", cmd)
            return ""
        except Exception:
            logger.exception("Failed to run QMD: {}", cmd)
            return ""

    def _start_periodic_updates(self) -> None:
        """Start background periodic indexing task."""
        if self._update_task is not None:
            return

        async def periodic_update():
            while True:
                await asyncio.sleep(self.update_interval)
                try:
                    await self._run_qmd("update", self.DEFAULT_COLLECTION)
                    if self.sessions_enabled:
                        await self._run_qmd("update", self.SESSIONS_COLLECTION)
                    logger.debug("QMD periodic update completed")
                except Exception:
                    logger.exception("QMD periodic update failed")

        self._update_task = asyncio.create_task(periodic_update())

    async def shutdown(self) -> None:
        """Stop periodic updates and cleanup."""
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

    def get_citation(self, result: dict[str, Any]) -> str:
        """Get citation string for a search result."""
        path = result.get("path", "")
        if path and "#" in path:
            return f"Source: {path}"
        elif path:
            return f"Source: {path}"
        return ""
