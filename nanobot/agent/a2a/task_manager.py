"""Task Manager for A2A task lifecycle management."""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """A2A Task states."""
    PENDING = "pending"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class A2ATask:
    """Represents an A2A task."""
    task_id: str
    target_agent: str
    task: str
    state: TaskState = TaskState.PENDING
    result: str | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None
    timeout_s: int = 600
    context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "target_agent": self.target_agent,
            "task": self.task,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "timeout_s": self.timeout_s,
            "context": self.context,
            "metadata": self.metadata,
        }


class TaskManager:
    """Manages A2A task lifecycle.
    
    Tracks:
    - Task creation and states
    - Timeout handling
    - Metrics (completed/failed counts)
    """

    def __init__(self):
        self._tasks: dict[str, A2ATask] = {}
        self._completed_count: int = 0
        self._failed_count: int = 0

    def create(
        self,
        task: str,
        target_agent: str,
        timeout_s: int = 600,
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> A2ATask:
        """Create a new A2A task.
        
        Args:
            task: Task description
            target_agent: Target subagent ID
            timeout_s: Timeout in seconds (default 600 = 10 min)
            context: Optional context data
            metadata: Optional metadata
            
        Returns:
            Created task
        """
        task_id = str(uuid.uuid4())[:8]
        new_task = A2ATask(
            task_id=task_id,
            target_agent=target_agent,
            task=task,
            timeout_s=timeout_s,
            context=context or {},
            metadata=metadata or {},
        )
        self._tasks[task_id] = new_task
        logger.info("Created A2A task {} -> {}: {}", task_id, target_agent, task[:50])
        return new_task

    def start(self, task_id: str) -> A2ATask | None:
        """Mark task as working (started processing)."""
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.WORKING
            task.started_at = time.time()
            logger.info("Task {} started", task_id)
        return task

    def complete(self, task_id: str, result: str) -> A2ATask | None:
        """Mark task as completed with result."""
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.COMPLETED
            task.result = result
            task.completed_at = time.time()
            self._completed_count += 1
            logger.info("Task {} completed in {:.1f}s", task_id, 
                       task.completed_at - task.created_at)
        return task

    def fail(self, task_id: str, error: str) -> A2ATask | None:
        """Mark task as failed with error."""
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.FAILED
            task.error = error
            task.completed_at = time.time()
            self._failed_count += 1
            logger.error("Task {} failed: {}", task_id, error)
        return task

    def timeout(self, task_id: str) -> A2ATask | None:
        """Mark task as timed out."""
        task = self._tasks.get(task_id)
        if task:
            task.state = TaskState.TIMEOUT
            task.error = f"Task timed out after {task.timeout_s}s"
            task.completed_at = time.time()
            self._failed_count += 1
            logger.warning("Task {} timed out", task_id)
        return task

    def cancel(self, task_id: str) -> A2ATask | None:
        """Cancel a pending task."""
        task = self._tasks.get(task_id)
        if task and task.state == TaskState.PENDING:
            task.state = TaskState.CANCELLED
            task.completed_at = time.time()
            logger.info("Task {} cancelled", task_id)
        return task

    def get(self, task_id: str) -> A2ATask | None:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_all(self, include_completed: bool = True) -> list[dict[str, Any]]:
        """List all tasks.
        
        Args:
            include_completed: Include completed tasks in list
            
        Returns:
            List of task dicts
        """
        tasks = []
        for task in self._tasks.values():
            if not include_completed and task.completed_at:
                continue
            tasks.append(task.to_dict())
        return sorted(tasks, key=lambda t: t["created_at"], reverse=True)

    def list_active(self) -> list[dict[str, Any]]:
        """List only active (pending/working) tasks."""
        return [
            task.to_dict() 
            for task in self._tasks.values() 
            if task.state in (TaskState.PENDING, TaskState.WORKING)
        ]

    def get_metrics(self) -> dict[str, Any]:
        """Get task metrics."""
        active = len([t for t in self._tasks.values() 
                     if t.state in (TaskState.PENDING, TaskState.WORKING)])
        return {
            "total_tasks": len(self._tasks),
            "active_tasks": active,
            "completed_count": self._completed_count,
            "failed_count": self._failed_count,
        }

    def check_timeouts(self) -> list[str]:
        """Check for tasks that timed out.
        
        Returns:
            List of task IDs that timed out
        """
        now = time.time()
        timed_out = []
        for task in self._tasks.values():
            if task.state == TaskState.WORKING and task.started_at:
                if now - task.started_at > task.timeout_s:
                    self.timeout(task.task_id)
                    timed_out.append(task.task_id)
        return timed_out

    def cleanup_old_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks.
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of tasks cleaned up
        """
        now = time.time()
        cutoff = now - (max_age_hours * 3600)
        to_remove = [
            task_id for task_id, task in self._tasks.items()
            if task.completed_at and task.completed_at < cutoff
        ]
        for task_id in to_remove:
            del self._tasks[task_id]
        return len(to_remove)