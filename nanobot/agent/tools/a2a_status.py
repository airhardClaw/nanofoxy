"""A2A Status Tool - Monitor subagent status and metrics."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.agent.a2a.registry import AgentRegistry
    from nanobot.agent.a2a.task_manager import TaskManager

logger = logging.getLogger(__name__)


class A2AStatusTool(Tool):
    """Tool for monitoring A2A subagent status and metrics.
    
    Shows:
    - Subagent status (enabled/disabled/running)
    - Active tasks
    - Task metrics (completed/failed counts)
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
        return "a2a_status"

    @property
    def description(self) -> str:
        return (
            "Monitor A2A subagent status and task metrics. "
            "Shows status of all subagents, active tasks, and completed/failed counts."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subagent_id": {
                    "type": "string",
                    "description": "Specific subagent to check (optional)",
                },
                "tasks": {
                    "type": "boolean",
                    "description": "Include task list in output",
                    "default": False,
                },
                "metrics": {
                    "type": "boolean",
                    "description": "Include metrics (completed/failed counts)",
                    "default": True,
                },
            },
        }

    async def execute(
        self,
        subagent_id: str | None = None,
        tasks: bool = False,
        metrics: bool = True,
        **kwargs: Any,
    ) -> str:
        """Get subagent status."""
        if subagent_id:
            return await self._status_single(subagent_id, tasks, metrics)
        return await self._status_all(tasks, metrics)

    async def _status_single(self, subagent_id: str, include_tasks: bool, include_metrics: bool) -> str:
        """Get status for a specific subagent."""
        config = self._registry.get(subagent_id)
        if not config:
            return f"Subagent '{subagent_id}' not found"
        
        lines = [f"=== {subagent_id} ==="]
        lines.append(f"Name: {config.get('name', subagent_id)}")
        lines.append(f"Role: {config.get('role', 'N/A')}")
        lines.append(f"Enabled: {config.get('enabled', False)}")
        
        caps = config.get("capabilities", [])
        if caps:
            lines.append(f"Capabilities: {', '.join(caps)}")
        
        if include_metrics:
            task_metrics = self._task_manager.get_metrics()
            lines.append(f"\nTask Metrics:")
            lines.append(f"  Active: {task_metrics['active_tasks']}")
            lines.append(f"  Completed: {task_metrics['completed_count']}")
            lines.append(f"  Failed: {task_metrics['failed_count']}")
        
        if include_tasks:
            active_tasks = self._task_manager.list_active()
            if active_tasks:
                lines.append(f"\nActive Tasks:")
                for t in active_tasks:
                    if t["target_agent"] == subagent_id:
                        lines.append(f"  - {t['task_id']}: {t['task'][:40]} ({t['state']})")
        
        return "\n".join(lines)

    async def _status_all(self, include_tasks: bool, include_metrics: bool) -> str:
        """Get status for all subagents."""
        agents = self._registry.list_all()
        metrics = self._task_manager.get_metrics() if include_metrics else None
        
        lines = ["=== A2A Status ==="]
        
        if include_metrics and metrics:
            lines.append(f"Metrics: {metrics['active_tasks']} active, "
                         f"{metrics['completed_count']} completed, "
                         f"{metrics['failed_count']} failed")
        
        lines.append(f"\nSubagents ({len(agents)}):")
        for agent in agents:
            caps = agent.get("capabilities", [])
            cap_str = f" [{', '.join(caps[:2])}]" if caps else ""
            lines.append(f"  • {agent['subagent_id']}: {agent.get('name', '')}{cap_str}")
        
        if include_tasks:
            active_tasks = self._task_manager.list_active()
            if active_tasks:
                lines.append(f"\nActive Tasks ({len(active_tasks)}):")
                for t in active_tasks:
                    lines.append(f"  - {t['task_id']} -> {t['target_agent']}: {t['task'][:40]}")
        
        return "\n".join(lines)