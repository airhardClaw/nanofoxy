"""Shell execution tool."""

import asyncio
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

from loguru import logger
from nanobot.agent.tools.base import Tool


# Sensitive environment variables to filter out (prevent leaking to exec)
_SENSITIVE_ENV_VARS = {
    "API_KEY", "APIKEY", "SECRET", "TOKEN", "PASSWORD", "PRIVATE_KEY",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "DATABASE_URL",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
    "DEEPSEEK_API_KEY", "DASHSCOPE_API_KEY", "MOONSHOT_API_KEY",
    "ZAI_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY",
    # Also filter nanobot-specific and common secret suffixes
}


def _is_sensitive_var(name: str) -> bool:
    """Check if env var name suggests it contains secrets."""
    name_upper = name.upper()
    for sensitive in _SENSITIVE_ENV_VARS:
        if name_upper.endswith(sensitive) or sensitive in name_upper:
            return True
    return False


def _get_clean_env(path_append: str = "") -> dict[str, str]:
    """Get a clean environment for exec, filtering sensitive vars.
    
    This prevents leaking API keys and secrets to the exec tool.
    """
    clean_env = {
        "HOME": os.environ.get("HOME", "/root"),
        "USER": os.environ.get("USER", "root"),
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "SHELL": os.environ.get("SHELL", "/bin/sh"),
        "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "en_US.UTF-8"),
        "TMPDIR": os.environ.get("TMPDIR", "/tmp"),
        "TERM": os.environ.get("TERM", "xterm-256color"),
    }
    
    # Copy only non-sensitive environment variables
    for key, value in os.environ.items():
        if not _is_sensitive_var(key):
            clean_env[key] = value
    
    if path_append:
        clean_env["PATH"] = clean_env["PATH"] + os.pathsep + path_append
    
    return clean_env


def _has_bwrap() -> bool:
    """Check if bwrap is available on the system."""
    return shutil.which("bwrap") is not None


class ExecTool(Tool):
    """Tool to execute shell commands."""

    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = False,
        path_append: str = "",
        use_sandbox: bool = False,
    ):
        self.timeout = timeout
        self.working_dir = working_dir
        self.deny_patterns = deny_patterns or [
            r"\brm\s+-[rf]{1,2}\b",          # rm -r, rm -rf, rm -fr
            r"\bdel\s+/[fq]\b",              # del /f, del /q
            r"\brmdir\s+/s\b",               # rmdir /s
            r"(?:^|[;&|]\s*)format\b",       # format (as standalone command only)
            r"\b(mkfs|diskpart)\b",          # disk operations
            r"\bdd\s+if=",                   # dd
            r">\s*/dev/sd",                  # write to disk
            r"\b(shutdown|reboot|poweroff)\b",  # system power
            r":\(\)\s*\{.*\};\s*:",          # fork bomb
        ]
        self.allow_patterns = allow_patterns or []
        self.restrict_to_workspace = restrict_to_workspace
        self.path_append = path_append
        self.use_sandbox = use_sandbox and _has_bwrap()

    @property
    def name(self) -> str:
        return "exec"

    _MAX_TIMEOUT = 600
    _MAX_OUTPUT = 10_000

    @property
    def description(self) -> str:
        return "Execute a shell command and return its output. Use with caution."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
                "timeout": {
                    "type": "integer",
                    "description": (
                        "Timeout in seconds. Increase for long-running commands "
                        "like compilation or installation (default 60, max 600)."
                    ),
                    "minimum": 1,
                    "maximum": 600,
                },
            },
            "required": ["command"],
        }

    async def execute(
        self, command: str, working_dir: str | None = None,
        timeout: int | None = None, **kwargs: Any,
    ) -> str:
        cwd = working_dir or self.working_dir or os.getcwd()
        guard_error = self._guard_command(command, cwd)
        if guard_error:
            return guard_error

        effective_timeout = min(timeout or self.timeout, self._MAX_TIMEOUT)

        # Use clean environment to prevent leaking secrets
        env = _get_clean_env(self.path_append)

        try:
            # Build the command with bwrap if sandboxing is enabled
            if self.use_sandbox:
                command = self._wrap_with_bwrap(command, cwd)

            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=effective_timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass
                finally:
                    if sys.platform != "win32":
                        try:
                            os.waitpid(process.pid, os.WNOHANG)
                        except (ProcessLookupError, ChildProcessError) as e:
                            logger.debug("Process already reaped or not found: {}", e)
                return f"Error: Command timed out after {effective_timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            output_parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(output_parts) if output_parts else "(no output)"

            # Head + tail truncation to preserve both start and end of output
            max_len = self._MAX_OUTPUT
            if len(result) > max_len:
                half = max_len // 2
                result = (
                    result[:half]
                    + f"\n\n... ({len(result) - max_len:,} chars truncated) ...\n\n"
                    + result[-half:]
                )

            return result

        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _guard_command(self, command: str, cwd: str) -> str | None:
        """Best-effort safety guard for potentially destructive commands."""
        cmd = command.strip()
        lower = cmd.lower()

        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return "Error: Command blocked by safety guard (dangerous pattern detected)"

        if self.allow_patterns:
            if not any(re.search(p, lower) for p in self.allow_patterns):
                return "Error: Command blocked by safety guard (not in allowlist)"

        from nanobot.security.network import contains_internal_url
        if contains_internal_url(cmd):
            return "Error: Command blocked by safety guard (internal/private URL detected)"

        if self.restrict_to_workspace:
            # Check for path traversal patterns (including URL-encoded)
            traversal_patterns = [
                "..\\",  # Windows backslash
                "../",   # Unix forward slash
                "..%2f", # URL-encoded
                "..%5c", # URL-encoded backslash
                "%2e%2e",  # Double dot encoded
                "%2e%2e%2f",  # ../ encoded
                "%2e%2e%5c",  # ..\ encoded
            ]
            cmd_lower = cmd.lower()
            for pattern in traversal_patterns:
                if pattern in cmd_lower:
                    return "Error: Command blocked by safety guard (path traversal detected)"

            cwd_path = Path(cwd).resolve()

            for raw in self._extract_absolute_paths(cmd):
                try:
                    expanded = os.path.expandvars(raw.strip())
                    p = Path(expanded).expanduser().resolve()
                except Exception:
                    continue
                if p.is_absolute() and cwd_path not in p.parents and p != cwd_path:
                    return "Error: Command blocked by safety guard (path outside working dir)"

        return None

    @staticmethod
    def _extract_absolute_paths(command: str) -> list[str]:
        win_paths = re.findall(r"[A-Za-z]:\\[^\s\"'|><;]+", command)   # Windows: C:\...
        posix_paths = re.findall(r"(?:^|[\s|>'\"])(/[^\s\"'>;|<]+)", command) # POSIX: /absolute only
        home_paths = re.findall(r"(?:^|[\s|>'\"])(~[^\s\"'>;|<]*)", command) # POSIX/Windows home shortcut: ~
        return win_paths + posix_paths + home_paths

    def _wrap_with_bwrap(self, command: str, cwd: str) -> str:
        """Wrap command with bwrap for sandboxed execution.

        Creates a minimal namespace with only necessary access.
        """
        # bwrap options:
        # --new-session: Create new session (isolation)
        # --die-with-parent: Kill sandbox when parent dies
        # --ro-bind / /: Read-only bind of root (prevents escaping)
        # --bind /cwd /cwd: Bind working directory
        # --tmpfs /tmp: Private tmpfs
        # --unshare-user: Unshare user namespace
        # --unshare-ipc: Unshare IPC namespace
        # --unshare-net: Unshare network (optional, commented out for usability)
        bwrap_cmd = [
            "bwrap",
            "--new-session",
            "--die-with-parent",
            "--ro-bind", "/", "/",
            "--bind", cwd, cwd,
            "--tmpfs", "/tmp",
            "--unshare-user",
            "--unshare-ipc",
            # "--unshare-net",  # Disabled by default - enable if strict isolation needed
        ]
        # Add shell wrapper
        return " ".join(bwrap_cmd) + f" /bin/sh -c {command!r}"
