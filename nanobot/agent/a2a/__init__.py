"""A2A (Agent-to-Agent) communication module for nanofoxy.

This module provides:
- Agent Registry: Discovery and registration of subagents
- Task Manager: Task lifecycle management
- Agent Cards: Metadata generation for subagents

A2A Protocol allows:
- Chief agent to communicate with subagents
- Subagents to communicate with each other (peer-to-peer)
- Task delegation and result tracking
"""

from nanobot.agent.a2a.registry import AgentRegistry
from nanobot.agent.a2a.task_manager import TaskManager, A2ATask, TaskState
from nanobot.agent.a2a.cards import AgentCard, generate_agent_card

__all__ = [
    "AgentRegistry",
    "TaskManager", 
    "A2ATask",
    "TaskState",
    "AgentCard",
    "generate_agent_card",
]