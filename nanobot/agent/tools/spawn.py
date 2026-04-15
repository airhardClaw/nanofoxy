"""Spawn tool for creating background subagents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.subagent import SubagentManager
    from nanobot.agent.a2a.registry import AgentRegistry


class SpawnTool(Tool):
    """Tool to spawn a subagent for background task execution.
    
    Also supports dynamic subagent creation via 'create' action.
    """

    def __init__(self, manager: SubagentManager, registry: Optional[AgentRegistry] = None):
        self._manager = manager
        self._registry = registry
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
            "'information-expert' to spawn a specialized subagent. "
            "Also supports 'create' action to dynamically register new subagents."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["spawn", "create", "list"],
                    "description": "Action to perform (spawn=default, create=new subagent, list=show all)",
                    "default": "spawn",
                },
                "task": {
                    "type": "string",
                    "description": "The task for the subagent to complete (for spawn action)",
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label for the task (for display)",
                },
                "role": {
                    "type": "string",
                    "description": "Role for specialized subagent: coding-expert, websearch-expert, file-handel-expert, information-expert",
                },
                "subagent_id": {
                    "type": "string",
                    "description": "Subagent identifier (e.g., coding_expert)",
                },
                "name": {
                    "type": "string",
                    "description": "Name for new subagent (for create action)",
                },
                "description": {
                    "type": "string",
                    "description": "Description for new subagent (for create action)",
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Capabilities for new subagent (for create action)",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str = "spawn",
        task: str = "",
        label: str | None = None,
        role: str | None = None,
        subagent_id: str | None = None,
        name: str | None = None,
        description: str | None = None,
        capabilities: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Execute spawn action."""
        if action == "list":
            return await self._list_subagents()
        
        if action == "create":
            if not name and not subagent_id:
                return "Error: name or subagent_id required for create action"
            if not self._registry:
                return "Error: A2A registry not available"
            return await self._create_subagent(
                name=name or subagent_id,
                description=description or "",
                role=role or name,
                capabilities=capabilities or [],
            )
        
        # Default: spawn
        if not task:
            return "Error: task required for spawn action"
        
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

    async def _list_subagents(self) -> str:
        """List available subagents."""
        if not self._registry:
            return "A2A registry not available"
        
        agents = self._registry.list_all()
        if not agents:
            return "No subagents configured"
        
        lines = ["Available subagents:"]
        for agent in agents:
            caps = agent.get("capabilities", [])
            lines.append(f"  - {agent['subagent_id']}: {agent.get('name', '')}")
            if caps:
                lines.append(f"    Capabilities: {', '.join(caps)}")
        
        return "\n".join(lines)

    async def _create_subagent(
        self,
        name: str,
        description: str,
        role: str,
        capabilities: list[str],
    ) -> str:
        """Create a new subagent configuration."""
        subagent_id = name.lower().replace(" ", "_").replace("-", "_")
        
        config = {
            "subagent_id": subagent_id,
            "name": name,
            "role": role,
            "description": description,
            "enabled": True,
            "capabilities": capabilities,
            "max_iterations": 15,
        }
        
        result = self._registry.register(config)
        if result.get("success"):
            return f"Created subagent: {subagent_id}"
        return f"Failed to create subagent: {result.get('error', 'Unknown error')}"
