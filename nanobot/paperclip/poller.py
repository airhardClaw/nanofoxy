"""Paperclip task poller service for nanobot."""

import asyncio
from datetime import datetime
from typing import Awaitable, Callable, Optional

from loguru import logger

from nanobot.paperclip.client import PaperclipClient
from nanobot.paperclip.models import Issue, IssueComment


class TaskHandler:
    """Callback handler for when a task is found."""

    async def on_task_found(self, issue: Issue) -> None:
        """Called when a new todo task is found."""
        pass

    async def on_task_claimed(self, issue: Issue) -> None:
        """Called when a task is successfully claimed."""
        pass

    async def on_task_completed(self, issue: Issue, result: str) -> None:
        """Called when a task is completed."""
        pass

    async def on_task_failed(self, issue: Issue, error: str) -> None:
        """Called when a task fails."""
        pass


class PaperclipTaskPoller:
    """Periodically polls Paperclip for new tasks assigned to this agent."""

    def __init__(
        self,
        api_url: str,
        company_id: str,
        agent_id: str,
        interval_seconds: int = 300,
        auto_claim: bool = True,
        on_task_found: Optional[Callable[[Issue], Awaitable[None]]] = None,
    ):
        self.client = PaperclipClient(
            api_url=api_url,
            company_id=company_id,
            agent_id=agent_id,
        )
        self.interval_seconds = interval_seconds
        self.auto_claim = auto_claim
        self.on_task_found = on_task_found
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._processed_ids: set[str] = set()

    async def start(self) -> None:
        """Start the poller."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Paperclip task poller started (interval: {self.interval_seconds}s)")

    async def stop(self) -> None:
        """Stop the poller."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.client.close()
        logger.info("Paperclip task poller stopped")

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_once()
            except Exception as e:
                logger.error(f"Paperclip polling error: {e}")

            await asyncio.sleep(self.interval_seconds)

    async def _poll_once(self) -> None:
        """Poll for new tasks once."""
        logger.debug("Polling for new Paperclip tasks...")

        try:
            todo_tasks = await self.client.get_todo_tasks()
            logger.debug(f"Found {len(todo_tasks)} todo tasks")

            for task in todo_tasks:
                if task.id in self._processed_ids:
                    continue

                self._processed_ids.add(task.id)
                logger.info(f"New task found: {task.to_summary()}")

                if self.on_task_found:
                    await self.on_task_found(task)

                if self.auto_claim:
                    await self._claim_task(task)
        except Exception as e:
            logger.error(f"Error polling Paperclip: {e}")
            raise

    async def _claim_task(self, task: Issue) -> None:
        """Claim a task and update its status."""
        try:
            updated = await self.client.claim_issue(task.id)
            logger.info(f"Claimed task: {updated.to_summary()}")
        except Exception as e:
            logger.error(f"Failed to claim task {task.id}: {e}")

    async def fetch_tasks(self) -> list[Issue]:
        """Manually fetch tasks (for manual trigger)."""
        try:
            tasks = await self.client.get_todo_tasks()
            for task in tasks:
                self._processed_ids.add(task.id)
            return tasks
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []

    async def get_all_tasks(self, status: Optional[str] = None) -> list[Issue]:
        """Get all tasks, optionally filtered by status."""
        try:
            if status:
                return await self.client.list_issues(status=status)
            return await self.client.list_issues()
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return []

    async def complete_task(self, issue_id: str, comment: Optional[str] = None) -> Issue:
        """Mark a task as completed and optionally add a comment."""
        issue = await self.client.complete_issue(issue_id)

        if comment:
            await self.client.add_comment(
                issue_id=issue_id,
                body=comment,
                author_agent_id=self.client.agent_id,
            )

        logger.info(f"Completed task: {issue.to_summary()}")
        return issue

    async def add_execution_log(
        self,
        issue_id: str,
        log: str,
        include_timestamp: bool = True,
    ) -> "IssueComment":
        """Add an execution log comment to a task."""
        timestamp = datetime.utcnow().isoformat()
        body = log if not include_timestamp else f"[{timestamp}]\n\n{log}"

        comment = await self.client.add_comment(
            issue_id=issue_id,
            body=body,
            author_agent_id=self.client.agent_id,
        )

        logger.debug(f"Added comment to issue {issue_id}")
        return comment
        return comment
