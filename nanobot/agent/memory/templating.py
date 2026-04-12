"""Jinja2 templating for agent responses and memory summaries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import BaseLoader, Environment, TemplateNotFound
from loguru import logger

from nanobot.utils.helpers import ensure_dir


class NanobotTemplateLoader(BaseLoader):
    """Custom Jinja2 loader that loads templates from the workspace memory directory."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory" / "templates")

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, bool]:
        """Load template from memory/templates directory."""
        template_path = self.memory_dir / template

        if not template_path.exists():
            template_path = Path(__file__).parent.parent.parent / "templates" / template

        if not template_path.exists():
            raise TemplateNotFound(template)

        mtime = template_path.stat().st_mtime
        return (template_path.read_text(encoding="utf-8"), str(template_path), mtime)


class TemplateEngine:
    """Jinja2 templating engine for agent responses and memory."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory_dir = ensure_dir(workspace / "memory")
        self.templates_dir = ensure_dir(self.memory_dir / "templates")
        self.loader = NanobotTemplateLoader(workspace)
        self.env = Environment(
            loader=self.loader,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

        self.env.filters["datetime"] = lambda x: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.env.filters["isoformat"] = lambda x: x.isoformat() if isinstance(x, datetime) else str(x)

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template_name: Name of template file.
            context: Variables to pass to template.

        Returns:
            Rendered template string.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context)
        except TemplateNotFound:
            logger.warning("Template '{}' not found", template_name)
            return ""
        except Exception as e:
            logger.warning("Template render error for '{}': {}", template_name, e)
            return ""

    def render_string(self, template_str: str, context: dict[str, Any]) -> str:
        """Render a template from a string.

        Args:
            template_str: Template string.
            context: Variables to pass to template.

        Returns:
            Rendered string.
        """
        try:
            template = self.env.from_string(template_str)
            return template.render(**context)
        except Exception as e:
            logger.warning("Template string render error: {}", e)
            return template_str

    def list_templates(self) -> list[str]:
        """List available templates."""
        templates = set()
        for ext in (".j2", ".md", ".txt", ".html"):
            templates.update(self.templates_dir.glob(f"*{ext}"))
        return [t.name for t in templates]

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False


def create_response_context(
    model: str,
    workspace: Path,
    session_key: str | None = None,
    user_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create standard context for response templates.

    Args:
        model: Model name being used.
        workspace: Workspace path.
        session_key: Current session key.
        user_info: Known user information.

    Returns:
        Context dict for template rendering.
    """
    return {
        "model": model,
        "workspace": str(workspace),
        "session": session_key,
        "user": user_info or {},
        "timestamp": datetime.now(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M:%S"),
    }


def create_memory_context(
    memory_file: Path,
    history_file: Path,
    recent_events: list[str] | None = None,
) -> dict[str, Any]:
    """Create context for memory consolidation templates.

    Args:
        memory_file: Path to MEMORY.md.
        history_file: Path to HISTORY.md.
        recent_events: List of recent events to include.

    Returns:
        Context dict for memory templates.
    """
    memory_content = ""
    if memory_file.exists():
        memory_content = memory_file.read_text(encoding="utf-8")

    return {
        "memory": memory_content,
        "recent_events": recent_events or [],
        "timestamp": datetime.now(),
    }
