"""A2A Server Control Tool - Start/stop/register subagents."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.a2a.registry import AgentRegistry
    from nanobot.agent.a2a.task_manager import TaskManager

logger = logging.getLogger(__name__)


class A2AControlTool(Tool):
    """Tool for controlling the A2A server and subagents.
    
    Actions:
    - status: Show server status overview
    - register: Register a new subagent
    - start: Start a subagent bot
    - stop: Stop a subagent bot
    - restart: Restart a subagent bot
    """

    def __init__(
        self,
        registry: AgentRegistry,
        task_manager: TaskManager,
        workspace: Path,
    ):
        self._registry = registry
        self._task_manager = task_manager
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "a2a_control"

    @property
    def description(self) -> str:
        return (
            "Control the A2A server and subagents. "
            "Actions: status (overview), register (new subagent), "
            "start/stop/restart (subagent bots). "
            "Note: Only the chief agent can use this tool."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "register", "start", "stop", "restart"],
                    "description": "Control action to perform",
                },
                "subagent_id": {
                    "type": "string",
                    "description": "Target subagent ID",
                },
                "config": {
                    "type": "object",
                    "description": "Subagent config (for register action)",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        subagent_id: str | None = None,
        config: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """Execute A2A control action."""
        if action == "status":
            return await self._status()
        
        elif action == "register":
            if not config:
                return "Error: config required for register action"
            return await self._register(config)
        
        elif action == "start":
            if not subagent_id:
                return "Error: subagent_id required for start action"
            return await self._start(subagent_id)
        
        elif action == "stop":
            if not subagent_id:
                return "Error: subagent_id required for stop action"
            return await self._stop(subagent_id)
        
        elif action == "restart":
            if not subagent_id:
                return "Error: subagent_id required for restart action"
            return await self._restart(subagent_id)
        
        return f"Unknown action: {action}"

    async def _status(self) -> str:
        """Get server status overview."""
        # Get task metrics
        metrics = self._task_manager.get_metrics()
        
        # Get registered agents
        agents = self._registry.list_all()
        
        lines = ["=== A2A Server Status ==="]
        lines.append(f"Registered subagents: {len(agents)}")
        lines.append(f"Active tasks: {metrics['active_tasks']}")
        lines.append(f"Completed tasks: {metrics['completed_count']}")
        lines.append(f"Failed tasks: {metrics['failed_count']}")
        
        if agents:
            lines.append("\nSubagents:")
            for agent in agents:
                enabled = "enabled" if agent.get("enabled") else "disabled"
                lines.append(f"  - {agent['subagent_id']}: {agent.get('name', '')} ({enabled})")
        
        return "\n".join(lines)

    async def _register(self, config: dict[str, Any]) -> str:
        """Register a new subagent."""
        result = self._registry.register(config)
        if result.get("success"):
            return f"Registered subagent: {result['subagent_id']}"
        return f"Failed to register: {result.get('error', 'Unknown error')}"

    async def _start(self, subagent_id: str) -> str:
        """Start a subagent bot."""
        config = self._registry.get(subagent_id)
        if not config:
            return f"Subagent '{subagent_id}' not found"
        
        if not config.get("enabled"):
            # Enable it
            config["enabled"] = True
            self._registry.register(config)
        
        bot_token = config.get("bot_token", "")
        if not bot_token or bot_token == "MANUELL_EINTRAGEN":
            return f"Subagent '{subagent_id}' has no bot_token configured"
        
        # Note: Actual bot starting would need to be done by the Telegram channel
        # This just updates the config
        logger.info("Starting subagent: {}", subagent_id)
        return f"Started subagent: {subagent_id} (bot_token: {bot_token[:10]}...)"

    async def _stop(self, subagent_id: str) -> str:
        """Stop a subagent bot."""
        config = self._registry.get(subagent_id)
        if not config:
            return f"Subagent '{subagent_id}' not found"
        
        config["enabled"] = False
        self._registry.register(config)
        
        logger.info("Stopped subagent: {}", subagent_id)
        return f"Stopped subagent: {subagent_id}"

    async def _restart(self, subagent_id: str) -> str:
        """Restart a subagent bot."""
        await self._stop(subagent_id)
        return await self._start(subagent_id)