"""Git-versioned storage for memory system - enables state recovery."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from nanobot.utils.helpers import ensure_dir


class GitMemoryStore:
    """Git-versioned memory storage with commit history."""

    def __init__(self, workspace: Path):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.git_dir = self.memory_dir / ".git"
        self._init_or_load_repo()

    def _init_or_load_repo(self) -> None:
        """Initialize git repo or load existing one."""
        try:
            from git import Actor, Repo

            if not self.git_dir.exists():
                self.repo = Repo.init(self.memory_dir)
                logger.info("Initialized git memory store at {}", self.memory_dir)
                config_writer = self.repo.config_writer()
                config_writer.set_value("user", "name", "nanobot")
                config_writer.set_value("user", "email", "nanobot@local")
            else:
                self.repo = Repo(self.memory_dir)

            self.actor = Actor("nanobot", "nanobot@local")
        except Exception as e:
            logger.warning("Failed to initialize git memory store: {}", e)
            self.repo = None

    def _ensure_working_dir(self) -> None:
        """Ensure the memory directory exists and is accessible."""
        if not self.memory_dir.exists():
            self.memory_dir.mkdir(parents=True, exist_ok=True)

    def commit(self, message: str | None = None) -> str | None:
        """Commit current memory state.

        Args:
            message: Commit message. Auto-generated if not provided.

        Returns:
            Commit hash if successful, None otherwise.
        """
        if not self.repo:
            return None

        try:
            self._ensure_working_dir()

            index = self.repo.index
            index.add(["."])
            index.add(["-u"])  # Also add untracked files

            if index.diff("HEAD"):
                msg = message or f"Memory update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                commit = index.commit(msg, author=self.actor, commit=self.actor)
                logger.debug("Committed memory state: {}", commit.hexsha[:7])
                return commit.hexsha
        except Exception as e:
            logger.debug("No commit needed or error: {}", e)
        return None

    def get_history(self, max_count: int = 10) -> list[dict[str, Any]]:
        """Get memory commit history.

        Args:
            max_count: Maximum number of commits to return.

        Returns:
            List of commit info dicts with hash, message, date.
        """
        if not self.repo:
            return []

        try:
            commits = list(self.repo.iter_commits("HEAD", max_count=max_count))
            return [
                {
                    "hash": c.hexsha[:7],
                    "full_hash": c.hexsha,
                    "message": c.message.strip(),
                    "author": str(c.author),
                    "date": c.committed_datetime.isoformat(),
                }
                for c in commits
            ]
        except Exception as e:
            logger.warning("Failed to get memory history: {}", e)
            return []

    def restore(self, commit_hash: str | None = None) -> bool:
        """Restore memory state to a specific commit or previous commit.

        Args:
            commit_hash: Full or partial commit hash. Uses HEAD~1 if None.

        Returns:
            True if restore successful.
        """
        if not self.repo:
            return False

        try:
            if commit_hash:
                commit = self.repo.commit(commit_hash)
            else:
                commit = self.repo.commit("HEAD~1")

            self.repo.git.checkout(commit, force=True)
            logger.info("Restored memory to commit: {}", commit.hexsha[:7])
            return True
        except Exception as e:
            logger.warning("Failed to restore memory: {}", e)
            return False

    def diff(self, commit_a: str = "HEAD", commit_b: str | None = None) -> str | None:
        """Get diff between commits.

        Args:
            commit_a: First commit (or "HEAD" for working dir).
            commit_b: Second commit (or None for working dir vs commit_a).

        Returns:
            Diff string or None on error.
        """
        if not self.repo:
            return None

        try:
            if commit_b:
                return self.repo.git.diff(commit_a, commit_b)
            return self.repo.git.diff(commit_a)
        except Exception as e:
            logger.debug("No diff available: {}", e)
            return None

    def status(self) -> dict[str, list[str]]:
        """Get current git status of memory directory.

        Returns:
            Dict with 'modified', 'staged', 'untracked' file lists.
        """
        if not self.repo:
            return {"modified": [], "staged": [], "untracked": []}

        try:
            status = self.repo.git.status("--porcelain")
            result = {"modified": [], "staged": [], "untracked": []}

            for line in status.split("\n"):
                if not line:
                    continue
                idx = line[:2]
                filepath = line[3:]

                if idx[0] == "?":
                    result["untracked"].append(filepath)
                elif idx[0] == "M":
                    result["modified"].append(filepath)
                elif idx[1] == "M":
                    result["staged"].append(filepath)

            return result
        except Exception:
            return {"modified": [], "staged": [], "untracked": []}

    def list_snapshots(self, max_count: int = 20) -> list[dict[str, Any]]:
        """List available memory snapshots (commits).

        Args:
            max_count: Maximum snapshots to return.

        Returns:
            List of snapshot info.
        """
        return self.get_history(max_count)


class MemoryVersionManager:
    """Manages memory versioning with auto-commits and recovery."""

    def __init__(self, workspace: Path, auto_commit: bool = True):
        self.workspace = workspace
        self.auto_commit = auto_commit
        self.git_store = GitMemoryStore(workspace)
        self._last_commit_time: datetime | None = None

    def save_and_commit(self, message: str | None = None) -> str | None:
        """Save memory and create a git commit.

        Args:
            message: Optional commit message.

        Returns:
            Commit hash if created, None otherwise.
        """
        commit_hash = self.git_store.commit(message)
        if commit_hash:
            self._last_commit_time = datetime.now()
        return commit_hash

    def auto_save(self) -> str | None:
        """Auto-save with timestamp message if enabled."""
        if not self.auto_commit:
            return None

        now = datetime.now()
        if self._last_commit_time:
            time_diff = (now - self._last_commit_time).total_seconds()
            if time_diff < 300:
                return None

        return self.save_and_commit()

    def get_snapshots(self, max_count: int = 20) -> list[dict[str, Any]]:
        """Get available memory snapshots."""
        return self.git_store.list_snapshots(max_count)

    def restore_snapshot(self, snapshot_id: str | None = None) -> bool:
        """Restore memory to a specific snapshot.

        Args:
            snapshot_id: Commit hash (partial or full). Uses previous if None.

        Returns:
            True if successful.
        """
        return self.git_store.restore(snapshot_id)

    def get_diff(self, since: str | None = None) -> str | None:
        """Get diff of memory changes since a commit.

        Args:
            since: Commit to compare from. Uses HEAD~1 if None.
        """
        if since:
            return self.git_store.diff(since, "HEAD")
        return self.git_store.diff("HEAD~1", "HEAD")
