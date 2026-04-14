"""Modular hooks system for memory and file writing operations.

Hooks are extensible callbacks that allow custom behavior at key points:
- Memory hooks: consolidation, recall, promotion
- File hooks: before/after write, backup, validation
- Tool hooks: pre/post execution (like Claude Code PreToolUse/PostToolUse)
- Agent lifecycle: start, stop, error

Inspired by Cloud Code API hooks (brainCloud) and Claude Code hooks:
- Pre hooks can modify parameters or block execution
- Post hooks can process results or modify output
- Failure hooks handle exceptions

Usage:
    from nanobot.agent.hooks import (
        MemoryHook,
        FileHook,
        ToolHook,
        HookRegistry,
    )

    class MyMemoryHook(MemoryHook):
        async def before_consolidate(self, messages: list[dict]) -> None:
            logger.info("About to consolidate {} messages", len(messages))

    # Tool pre-hook can block dangerous commands
    class SecurityToolHook(ToolHook):
        async def before_execute(self, tool_name: str, args: dict) -> bool | dict:
            if tool_name == "Bash" and "rm -rf" in args.get("command", ""):
                return {"error": "Blocked dangerous command"}
            return True  # Allow

    registry = HookRegistry()
    registry.register_memory_hook(MyMemoryHook())
    registry.register_tool_hook(SecurityToolHook())
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypeVar, runtime_checkable

from loguru import logger

if TYPE_CHECKING:
    from nanobot.agent.memory.store import MemoryStore

T = TypeVar("T")


@runtime_checkable
class MemoryHook(Protocol):
    """Protocol for memory-related hooks."""

    async def before_consolidate(self, messages: list[dict[str, Any]]) -> None:
        """Called before memory consolidation starts."""
        ...

    async def after_consolidate(self, success: bool, message_count: int) -> None:
        """Called after memory consolidation completes."""
        ...

    async def on_recall(self, entry_id: str, query: str, score: float) -> None:
        """Called when a memory is recalled."""
        ...

    async def on_promote(self, entry_id: str, score: float) -> None:
        """Called when a memory entry is promoted to durable storage."""
        ...

    async def on_theme_detected(self, theme: str, strength: float) -> None:
        """Called when a theme is detected in REM sleep."""
        ...


@runtime_checkable
class FileHook(Protocol):
    """Protocol for file writing hooks."""

    async def before_write(
        self,
        path: Path,
        content: str,
        create_backup: bool,
    ) -> tuple[Path, str, bool] | None:
        """Called before file write. Return modified (path, content, create_backup) or None."""
        return None

    async def after_write(self, path: Path, bytes_written: int) -> None:
        """Called after file write completes."""
        ...

    async def on_backup_created(self, backup_path: Path, original_path: Path) -> None:
        """Called when a backup is created before writing."""
        ...

    async def validate_content(self, path: Path, content: str) -> bool | str:
        """Validate content before writing. Return True to allow, or error message to reject."""
        return True


@runtime_checkable
class ToolHook(Protocol):
    """Protocol for tool execution hooks (like Claude Code PreToolUse/PostToolUse)."""

    async def before_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool | dict[str, Any]:
        """Pre-tool hook. Return True to allow, or error dict to block."""
        return True

    async def after_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
        success: bool,
    ) -> None:
        """Post-tool hook. Called after tool execution."""
        ...

    async def on_error(
        self,
        tool_name: str,
        args: dict[str, Any],
        error: str,
    ) -> None:
        """On tool execution error."""
        ...


    async def can_match(self, tool_name: str) -> bool:
        """Matcher - return True if this hook applies to this tool."""
        return True


@runtime_checkable
class AgentLifecycleHook(Protocol):
    """Protocol for agent lifecycle hooks."""

    async def on_start(self, session_key: str, messages: list[dict[str, Any]]) -> None:
        """Called when agent starts."""
        ...

    async def on_stop(
        self,
        session_key: str,
        reason: str,
        stats: dict[str, Any],
    ) -> None:
        """Called when agent stops."""
        ...

    async def on_error(self, session_key: str, error: str, context: dict[str, Any]) -> None:
        """Called on agent error."""
        ...


    async def on_message(self, message: dict[str, Any]) -> None:
        """Called on each message (user/assistant)."""
        ...


@dataclass
class HookContext:
    """Context passed to hooks."""

    workspace: Path
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class HookRegistry:
    """Central registry for managing hooks."""

    def __init__(self):
        self._memory_hooks: list[MemoryHook] = []
        self._file_hooks: list[FileHook] = []
        self._tool_hooks: list[ToolHook] = []
        self._lifecycle_hooks: list[AgentLifecycleHook] = []
        self._enabled: bool = True

    def register_memory_hook(self, hook: MemoryHook) -> None:
        """Register a memory hook."""
        self._memory_hooks.append(hook)
        logger.info("Registered memory hook: {}", type(hook).__name__)

    def register_file_hook(self, hook: FileHook) -> None:
        """Register a file hook."""
        self._file_hooks.append(hook)
        logger.info("Registered file hook: {}", type(hook).__name__)

    def register_tool_hook(self, hook: ToolHook) -> None:
        """Register a tool hook."""
        self._tool_hooks.append(hook)
        logger.info("Registered tool hook: {}", type(hook).__name__)

    def register_lifecycle_hook(self, hook: AgentLifecycleHook) -> None:
        """Register an agent lifecycle hook."""
        self._lifecycle_hooks.append(hook)
        logger.info("Registered lifecycle hook: {}", type(hook).__name__)

    def unregister_memory_hook(self, hook: MemoryHook) -> None:
        """Unregister a memory hook."""
        self._memory_hooks.remove(hook)

    def unregister_file_hook(self, hook: FileHook) -> None:
        """Unregister a file hook."""
        self._file_hooks.remove(hook)

    def unregister_tool_hook(self, hook: ToolHook) -> None:
        """Unregister a tool hook."""
        self._tool_hooks.remove(hook)

    def unregister_lifecycle_hook(self, hook: AgentLifecycleHook) -> None:
        """Unregister a lifecycle hook."""
        self._lifecycle_hooks.remove(hook)

    @property
    def memory_hooks(self) -> list[MemoryHook]:
        return self._memory_hooks

    @property
    def file_hooks(self) -> list[FileHook]:
        return self._file_hooks

    @property
    def tool_hooks(self) -> list[ToolHook]:
        return self._tool_hooks

    @property
    def lifecycle_hooks(self) -> list[AgentLifecycleHook]:
        return self._lifecycle_hooks

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        logger.info("Hooks enabled: {}", value)


_global_registry: HookRegistry | None = None


def get_global_registry() -> HookRegistry:
    """Get the global hooks registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = HookRegistry()
    return _global_registry


async def dispatch_memory_hooks(
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Dispatch a call to all memory hooks."""
    registry = get_global_registry()
    if not registry.enabled:
        return

    for hook in registry.memory_hooks:
        if not isinstance(hook, MemoryHook):
            continue
        method_func = getattr(hook, method, None)
        if method_func and callable(method_func):
            try:
                await method_func(*args, **kwargs)
            except Exception:
                logger.exception("Hook {} failed: {}", method, type(hook).__name__)


async def dispatch_file_hooks(
    method: str,
    *args: Any,
    **kwargs: Any,
) -> tuple[Any, ...] | None:
    """Dispatch a call to all file hooks. Returns modified args from before_write hooks."""
    registry = get_global_registry()
    if not registry.enabled:
        return None

    for hook in registry.file_hooks:
        if not isinstance(hook, FileHook):
            continue
        method_func = getattr(hook, method, None)
        if method_func and callable(method_func):
            try:
                result = await method_func(*args, **kwargs)
                if method == "before_write" and result is not None:
                    return result
            except Exception:
                logger.exception("Hook {} failed: {}", method, type(hook).__name__)
    return None


async def dispatch_tool_hooks(
    method: str,
    *args: Any,
    **kwargs: Any,
) -> bool | dict[str, Any] | None:
    """Dispatch a call to tool hooks. Returns False/block dict to block, modified args, or None."""
    registry = get_global_registry()
    if not registry.enabled:
        return None

    tool_name = args[0] if args else ""
    for hook in registry.tool_hooks:
        if not isinstance(hook, ToolHook):
            continue
        if method == "before_execute":
            if not hook.can_match(tool_name):
                continue
        method_func = getattr(hook, method, None)
        if method_func and callable(method_func):
            try:
                result = await method_func(*args, **kwargs)
                if result is not True:
                    return result
            except Exception:
                logger.exception("Tool hook {} failed: {}", method, type(hook).__name__)
    return None


async def dispatch_lifecycle_hooks(
    method: str,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Dispatch a call to lifecycle hooks."""
    registry = get_global_registry()
    if not registry.enabled:
        return

    for hook in registry.lifecycle_hooks:
        if not isinstance(hook, AgentLifecycleHook):
            continue
        method_func = getattr(hook, method, None)
        if method_func and callable(method_func):
            try:
                await method_func(*args, **kwargs)
            except Exception:
                logger.exception("Lifecycle hook {} failed: {}", method, type(hook).__name__)


class LoggingMemoryHook:
    """Built-in hook that logs memory operations."""

    async def before_consolidate(self, messages: list[dict[str, Any]]) -> None:
        logger.debug("Memory consolidation: {} messages", len(messages))

    async def after_consolidate(self, success: bool, message_count: int) -> None:
        status = "success" if success else "failed"
        logger.info("Memory consolidation {}: {} messages", status, message_count)

    async def on_recall(self, entry_id: str, query: str, score: float) -> None:
        logger.debug("Recall: {} (score: {:.2f})", entry_id, score)

    async def on_promote(self, entry_id: str, score: float) -> None:
        logger.info("Promoted: {} (score: {:.2f})", entry_id, score)

    async def on_theme_detected(self, theme: str, strength: float) -> None:
        logger.info("Theme detected: {} (strength: {:.2f})", theme, strength)


class LoggingFileHook:
    """Built-in hook that logs file operations."""

    async def before_write(
        self,
        path: Path,
        content: str,
        create_backup: bool,
    ) -> tuple[Path, str, bool] | None:
        logger.debug("File write: {} ({} bytes, backup: {})", path, len(content), create_backup)
        return None

    async def after_write(self, path: Path, bytes_written: int) -> None:
        logger.info("File written: {} ({} bytes)", path, bytes_written)

    async def on_backup_created(self, backup_path: Path, original_path: Path) -> None:
        logger.info("Backup created: {} -> {}", original_path, backup_path)

    async def validate_content(self, path: Path, content: str) -> bool | str:
        return True


class ValidationFileHook:
    """Built-in hook that validates file content before writing."""

    def __init__(
        self,
        max_file_size: int = 10 * 1024 * 1024,
        allowed_extensions: list[str] | None = None,
        blocked_patterns: list[str] | None = None,
    ):
        self.max_file_size = max_file_size
        self.allowed_extensions = allowed_extensions or [".md", ".txt", ".json", ".py", ".yaml", ".yml"]
        self.blocked_patterns = blocked_patterns or []

    async def validate_content(self, path: Path, content: str) -> bool | str:
        if len(content) > self.max_file_size:
            return f"File too large: {len(content)} bytes (max: {self.max_file_size})"

        ext = path.suffix.lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            return f"Extension not allowed: {ext}"

        for pattern in self.blocked_patterns:
            if pattern in content:
                return f"Blocked pattern found: {pattern}"

        return True


class BackupFileHook:
    """Built-in hook that creates backups before writing."""

    def __init__(self, max_backups: int = 5, backup_dir: Path | None = None):
        self.max_backups = max_backups
        self.backup_dir = backup_dir

    async def before_write(
        self,
        path: Path,
        content: str,
        create_backup: bool,
    ) -> tuple[Path, str, bool] | None:
        if not create_backup or not path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.parent / f"{path.name}.bak.{timestamp}"

        if self.backup_dir:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = self.backup_dir / f"{path.name}.{timestamp}"

        try:
            backup_path.write_text(content, encoding="utf-8")
            logger.info("Backup created: {}", backup_path)
        except Exception:
            logger.warning("Failed to create backup: {}", backup_path)

        return None

    async def on_backup_created(self, backup_path: Path, original_path: Path) -> None:
        pass


class RateLimitMemoryHook:
    """Built-in hook that rate-limits consolidation to prevent abuse."""

    def __init__(self, min_interval_seconds: int = 60):
        self.min_interval = min_interval_seconds
        self._last_consolidate: datetime | None = None

    async def before_consolidate(self, messages: list[dict[str, Any]]) -> None:
        now = datetime.now()
        if self._last_consolidate:
            elapsed = (now - self._last_consolidate).total_seconds()
            if elapsed < self.min_interval:
                logger.warning(
                    "Consolidation rate limited: {:.0f}s since last (min: {}s)",
                    elapsed,
                    self.min_interval,
                )
        self._last_consolidate = now


class MetricsMemoryHook:
    """Built-in hook that collects memory operation metrics."""

    def __init__(self):
        self.consolidate_count = 0
        self.consolidate_failures = 0
        self.recall_count = 0
        self.promote_count = 0

    async def after_consolidate(self, success: bool, message_count: int) -> None:
        self.consolidate_count += 1
        if not success:
            self.consolidate_failures += 1

    async def on_recall(self, entry_id: str, query: str, score: float) -> None:
        self.recall_count += 1

    async def on_promote(self, entry_id: str, score: float) -> None:
        self.promote_count += 1

    def get_metrics(self) -> dict[str, Any]:
        return {
            "consolidate_count": self.consolidate_count,
            "consolidate_failures": self.consolidate_failures,
            "recall_count": self.recall_count,
            "promote_count": self.promote_count,
            "success_rate": (
                (self.consolidate_count - self.consolidate_failures) / self.consolidate_count
                if self.consolidate_count > 0
                else 0
            ),
        }


class SecurityToolHook:
    """Built-in hook that blocks dangerous commands (like Claude Code PreToolUse)."""

    BLOCKED_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        ":(){:|:&};:",
        "mkfs",
        "dd if=/dev/zero of=/dev/",
    ]

    def __init__(self, blocked_patterns: list[str] | None = None):
        self.blocked_patterns = blocked_patterns or self.BLOCKED_PATTERNS

    async def before_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool | dict[str, Any]:
        if tool_name != "Bash":
            return True
        command = args.get("command", "")
        for pattern in self.blocked_patterns:
            if pattern in command:
                logger.warning("Blocked dangerous command: {}", command[:50])
                return {"error": f"Blocked dangerous command pattern: {pattern}"}
        return True

    async def after_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
        success: bool,
    ) -> None:
        pass

    async def on_error(
        self,
        tool_name: str,
        args: dict[str, Any],
        error: str,
    ) -> None:
        pass

    async def can_match(self, tool_name: str) -> bool:
        return tool_name == "Bash"


class LoggingToolHook:
    """Built-in hook that logs tool executions."""

    async def before_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool | dict[str, Any]:
        preview = str(args)[:80]
        logger.debug("Tool execute: {} args={}", tool_name, preview)
        return True

    async def after_execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: str,
        success: bool,
    ) -> None:
        status = "success" if success else "failed"
        logger.info("Tool {} {}", tool_name, status)

    async def on_error(
        self,
        tool_name: str,
        args: dict[str, Any],
        error: str,
    ) -> None:
        logger.warning("Tool {} error: {}", tool_name, error[:100])

    async def can_match(self, tool_name: str) -> bool:
        return True


class LoggingLifecycleHook:
    """Built-in hook that logs agent lifecycle events."""

    def __init__(self):
        self.start_time: datetime | None = None

    async def on_start(self, session_key: str, messages: list[dict[str, Any]]) -> None:
        self.start_time = datetime.now()
        logger.info("Agent started: {} ({} messages)", session_key, len(messages))

    async def on_stop(
        self,
        session_key: str,
        reason: str,
        stats: dict[str, Any],
    ) -> None:
        duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        logger.info(
            "Agent stopped: {} reason={} duration={:.1f}s stats={}",
            session_key,
            reason,
            duration,
            stats,
        )

    async def on_error(self, session_key: str, error: str, context: dict[str, Any]) -> None:
        logger.error("Agent error: {} error={}", session_key, error[:100])

    async def on_message(self, message: dict[str, Any]) -> None:
        role = message.get("role", "?")
        content = str(message.get("content", ""))[:50]
        logger.debug("Message: {} {}", role, content)


def install_default_hooks() -> None:
    """Install the default set of hooks."""
    registry = get_global_registry()
    registry.register_memory_hook(LoggingMemoryHook())
    registry.register_file_hook(LoggingFileHook())
    registry.register_tool_hook(LoggingToolHook())
    registry.register_lifecycle_hook(LoggingLifecycleHook())
    logger.info("Default hooks installed")