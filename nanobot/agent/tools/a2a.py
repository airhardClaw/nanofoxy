"""A2A Communication Tool - Call, forward, delegate tasks to subagents."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.a2a.registry import AgentRegistry
    from nanobot.agent.a2a.task_manager import TaskManager
    from nanobot.agent.subagent import SubagentManager

logger = logging.getLogger(__name__)


class A2ATool(Tool):
    """Tool for A2A communication with subagents.
    
    Actions:
    - list: List all available subagents
    - discover: Find subagents by capabilities
    - call: Call a specific subagent with a task
    - forward: Forward task to any capable subagent
    - delegate: Delegate task to multiple subagents
    """

    def __init__(
        self,
        registry: AgentRegistry,
        task_manager: TaskManager,
        subagent_manager: SubagentManager,
    ):
        self._registry = registry
        self._task_manager = task_manager
        self._subagent_manager = subagent_manager

    @property
    def name(self) -> str:
        return "a2a"

    @property
    def description(self) -> str:
        return (
            "Communicate with subagents via A2A protocol. "
            "Use this to delegate tasks to specialized subagents. "
            "Actions: list (show all), discover (by capability), call (specific), "
            "forward (any capable), delegate (multiple)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "discover", "call", "forward", "delegate"],
                    "description": "A2A action to perform",
                },
                "target": {
                    "type": "string",
                    "description": "Target subagent_id (for 'call' action)",
                },
                "capabilities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required capabilities (for 'discover' action)",
                },
                "task": {
                    "type": "string",
                    "description": "Task description for the subagent",
                },
                "agents": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of subagent IDs (for 'delegate' action)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 600 = 10 min)",
                    "default": 600,
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        target: str | None = None,
        capabilities: list[str] | None = None,
        task: str | None = None,
        agents: list[str] | None = None,
        timeout: int = 600,
        **kwargs: Any,
    ) -> str:
        """Execute A2A action."""
        if action == "list":
            return await self._list_agents()
        
        elif action == "discover":
            if not capabilities:
                return "Error: capabilities required for discover action"
            return await self._discover_agents(capabilities)
        
        elif action == "call":
            if not target or not task:
                return "Error: target and task required for call action"
            return await self._call_agent(target, task, timeout)
        
        elif action == "forward":
            if not task:
                return "Error: task required for forward action"
            return await self._forward_task(task, timeout)
        
        elif action == "delegate":
            if not agents or not task:
                return "Error: agents and task required for delegate action"
            return await self._delegate_task(agents, task, timeout)
        
        return f"Unknown action: {action}"

    async def _list_agents(self) -> str:
        """List all available subagents."""
        agents = self._registry.list_all()
        if not agents:
            return "No subagents registered"
        
        lines = ["Available Subagents:"]
        for agent in agents:
            caps = agent.get("capabilities", [])
            lines.append(f"  - {agent['subagent_id']}: {agent.get('name', '')}")
            if caps:
                lines.append(f"    Capabilities: {', '.join(caps)}")
        
        return "\n".join(lines)

    async def _discover_agents(self, capabilities: list[str]) -> str:
        """Discover subagents by capabilities."""
        agents = self._registry.discover(capabilities)
        if not agents:
            return f"No subagents found with capabilities: {capabilities}"
        
        lines = [f"Subagents with {capabilities}:"]
        for agent in agents:
            lines.append(f"  - {agent['subagent_id']}: {agent.get('name', '')}")
        
        return "\n".join(lines)

    async def _call_agent(self, target: str, task: str, timeout: int) -> str:
        """Call a specific subagent with a task."""
        # Get subagent config
        config = self._registry.get(target)
        if not config:
            return f"Error: Subagent '{target}' not found"
        
        if not config.get("enabled", True):
            return f"Error: Subagent '{target}' is disabled"
        
        role = config.get("role", target)
        
        # Create task in task manager
        a2a_task = self._task_manager.create(
            task=task,
            target_agent=target,
            timeout_s=timeout,
        )
        
        # Start task
        self._task_manager.start(a2a_task.task_id)
        
        # Execute via subagent manager
        try:
            result = await self._subagent_manager.spawn_with_role(
                task=task,
                role=role,
                subagent_id=target,
                origin_channel="cli",
                origin_chat_id="a2a",
                session_key=f"a2a:{a2a_task.task_id}",
            )
            
            # Complete task (the subagent spawn returns immediately, 
            # actual result comes via message bus)
            self._task_manager.complete(a2a_task.task_id, "Task initiated")
            return f"Task {a2a_task.task_id} sent to {target}: {result}"
            
        except Exception as e:
            self._task_manager.fail(a2a_task.task_id, str(e))
            return f"Error calling subagent {target}: {str(e)}"

    async def _forward_task(self, task: str, timeout: int) -> str:
        """Forward task to any capable subagent."""
        # Try to find subagent with matching capabilities from task
        # For now, just pick the first available
        agents = self._registry.list_all()
        if not agents:
            return "Error: No subagents available"
        
        # Pick first available agent
        target = agents[0]["subagent_id"]
        return await self._call_agent(target, task, timeout)

    async def _delegate_task(self, agents: list[str], task: str, timeout: int) -> str:
        """Delegate task to multiple subagents."""
        results = []
        for agent_id in agents:
            result = await self._call_agent(agent_id, task, timeout)
            results.append(f"{agent_id}: {result}")
        
        return "Delegated to:\n" + "\n".join(results)