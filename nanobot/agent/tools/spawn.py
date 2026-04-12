"""Spawn tool for creating background subagents."""

from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager


class SpawnTool(Tool):
    """Tool to spawn a subagent for background task execution."""

    def __init__(self, manager: "SubagentManager"):
        self._manager = manager
        self._origin_channel = "cli"
        self._origin_chat_id = "direct"
        self._session_key = "cli:direct"

    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the origin context for subagent announcements."""
        self._origin_channel = channel
        self._origin_chat_id = chat_id
        self._session_key = f"{channel}:{chat_id}"

    @property
    def name(self) -> str:
        return "spawn"

    @property
    def description(self) -> str:
        return (
            "Spawn a subagent to handle a task in the background. "
            "Use this for complex or time-consuming tasks that can run independently. "
            "The subagent will complete the task and report back when done. "
            "For deliverables or existing projects, inspect the workspace first "
            "and use a dedicated subdirectory when helpful. "
            "Use role='coding-expert', 'websearch-expert', 'file-handel-expert', or "
            "'information-expert' to spawn a specialized subagent."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
                "role": {
                    "type": "string",
                    "description": "Optional role for specialized subagent: coding-expert, websearch-expert, file-handel-expert, information-expert",
                },
                "subagent_id": {
                    "type": "string",
                    "description": "Subagent identifier (e.g., coding_expert, websearch_expert) - required if role is specified",
                },
            },
            "required": ["task"],
        }

    async def execute(self, task: str, label: str | None = None, role: str | None = None, subagent_id: str | None = None, **kwargs: Any) -> str:
        """Spawn a subagent to execute the given task."""
        # If role is specified, use spawn_with_role
        if role and subagent_id:
            return await self._manager.spawn_with_role(
                task=task,
                role=role,
                subagent_id=subagent_id,
                origin_channel=self._origin_channel,
                origin_chat_id=self._origin_chat_id,
                session_key=self._session_key,
            )

        # Default: use regular spawn
        return await self._manager.spawn(
            task=task,
            label=label,
            origin_channel=self._origin_channel,
            origin_chat_id=self._origin_chat_id,
            session_key=self._session_key,
        )
