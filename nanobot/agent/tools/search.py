"""Built-in search tools: grep and glob."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class GlobTool(Tool):
    """Find files matching a glob pattern."""

    name = "glob"
    description = "Find files matching a glob pattern (e.g. **/*.py). Returns list of file paths."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"},
            "path": {"type": "string", "description": "Root directory to search (default: workspace)"},
        },
        "required": ["pattern"],
    }

    def __init__(self, workspace: Path | None = None, restrict_to_workspace: bool = True):
        self.workspace = workspace or Path.cwd()
        self.restrict_to_workspace = restrict_to_workspace

    def _validate_path(self, path: Path) -> bool:
        """Ensure path is within allowed scope."""
        if not self.restrict_to_workspace:
            return True
        try:
            resolved = path.resolve().relative_to(self.workspace.resolve())
            return not resolved.startswith("..")
        except ValueError:
            return False

    async def execute(self, pattern: str, path: str | None = None, **kwargs: Any) -> str:
        root = self.workspace
        if path:
            root = Path(path).expanduser()
            if not self._validate_path(root):
                return f"Error: Path '{path}' is outside the allowed workspace"

        try:
            files = list(root.glob(pattern))
        except Exception as e:
            return f"Error: glob failed: {e}"

        valid_files = [f for f in files if self._validate_path(f)]
        if not valid_files:
            return f"No files found matching '{pattern}'"

        lines = [f"Files matching '{pattern}':"]
        for f in sorted(valid_files):
            rel = f.relative_to(self.workspace) if f.is_relative_to(self.workspace) else f
            lines.append(f"  {rel}")
        return "\n".join(lines)


class GrepTool(Tool):
    """Search for text patterns in files."""

    name = "grep"
    description = "Search for text patterns in files. Returns matching lines with context."
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "path": {"type": "string", "description": "File or directory to search"},
            "ignore_case": {"type": "boolean", "description": "Case insensitive search"},
            "max_results": {"type": "integer", "description": "Max matching lines", "default": 50},
        },
        "required": ["pattern", "path"],
    }

    def __init__(self, workspace: Path | None = None, restrict_to_workspace: bool = True):
        self.workspace = workspace or Path.cwd()
        self.restrict_to_workspace = restrict_to_workspace

    def _validate_path(self, path: Path) -> bool:
        """Ensure path is within allowed scope."""
        if not self.restrict_to_workspace:
            return True
        try:
            resolved = path.resolve().relative_to(self.workspace.resolve())
            return not resolved.startswith("..")
        except ValueError:
            return False

    async def execute(
        self,
        pattern: str,
        path: str,
        ignore_case: bool = False,
        max_results: int = 50,
        **kwargs: Any,
    ) -> str:
        search_path = Path(path).expanduser()
        if not self._validate_path(search_path):
            return f"Error: Path '{path}' is outside the allowed workspace"

        flags = re.IGNORECASE if ignore_case else 0
        try:
            compiled = re.compile(pattern, flags)
        except re.error as e:
            return f"Error: Invalid regex pattern: {e}"

        matches: list[tuple[Path, int, str]] = []

        if search_path.is_file():
            files_to_search = [search_path]
        elif search_path.is_dir():
            files_to_search = [f for f in search_path.rglob("*") if f.is_file() and not f.is_symlink()]
        else:
            return f"Error: Path '{path}' does not exist"

        for file_path in files_to_search:
            if not self._validate_path(file_path):
                continue
            # Skip binary files
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if compiled.search(line):
                            matches.append((file_path, line_num, line.rstrip()))
                            if len(matches) >= max_results:
                                break
            except (UnicodeDecodeError, OSError):
                continue

            if len(matches) >= max_results:
                break

        if not matches:
            return f"No matches found for '{pattern}'"

        lines = [f"Results for '{pattern}':"]
        for file_path, line_num, line in matches[:max_results]:
            rel = file_path.relative_to(self.workspace) if file_path.is_relative_to(self.workspace) else file_path
            lines.append(f"  {rel}:{line_num}: {line}")
        return "\n".join(lines)
