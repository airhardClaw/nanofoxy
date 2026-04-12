"""Paperclip tool for nanobot agent."""

from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.paperclip.client import PaperclipClient
from nanobot.paperclip.models import CreateIssueRequest, UpdateIssueRequest


class PaperclipTool(Tool):
    """Tool for interacting with Paperclip task management system."""

    name = "paperclip"
    description = """Interact with Paperclip task management system. Use this tool to:
- List and fetch tasks from Paperclip
- Get details of specific tasks
- Update task status and priority
- Add comments to tasks
- Create new tasks

All operations require the issue_id for specific tasks."""

    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "description": "The action to perform",
                "enum": [
                    "list_tasks",
                    "get_task",
                    "update_task",
                    "add_comment",
                    "create_task",
                    "fetch_my_tasks",
                ],
            },
            "status": {
                "type": "string",
                "description": "Filter tasks by status (backlog, todo, in_progress, in_review, done, blocked, cancelled)",
            },
            "issue_id": {
                "type": "string",
                "description": "The ID of the issue/task to operate on",
            },
            "title": {
                "type": "string",
                "description": "Title for creating a new task",
            },
            "description": {
                "type": "string",
                "description": "Description for creating or updating a task",
            },
            "new_status": {
                "type": "string",
                "description": "New status for updating a task (backlog, todo, in_progress, in_review, done, blocked, cancelled)",
            },
            "priority": {
                "type": "string",
                "description": "Priority level (critical, high, medium, low)",
            },
            "comment": {
                "type": "string",
                "description": "Comment text to add to a task",
            },
            "project_id": {
                "type": "string",
                "description": "Project ID to assign the task to",
            },
        },
        "required": ["action"],
    }

    def __init__(
        self,
        api_url: str = "http://127.0.0.1:3100",
        company_id: str = "",
        agent_id: str = "",
    ):
        self.client = PaperclipClient(
            api_url=api_url,
            company_id=company_id,
            agent_id=agent_id,
        )

    async def execute(self, **kwargs: Any) -> Any:
        """Execute the requested action."""
        action = kwargs.get("action")

        if action == "list_tasks":
            return await self._list_tasks(kwargs)
        elif action == "get_task":
            return await self._get_task(kwargs)
        elif action == "update_task":
            return await self._update_task(kwargs)
        elif action == "add_comment":
            return await self._add_comment(kwargs)
        elif action == "create_task":
            return await self._create_task(kwargs)
        elif action == "fetch_my_tasks":
            return await self._fetch_my_tasks()
        else:
            return {"error": f"Unknown action: {action}"}

    async def _list_tasks(self, kwargs: dict) -> dict:
        """List tasks with optional filters."""
        try:
            status = kwargs.get("status")
            priority = kwargs.get("priority")
            project_id = kwargs.get("project_id")

            tasks = await self.client.list_issues(
                status=status,
                priority=priority,
                project_id=project_id,
            )

            if not tasks:
                return {"message": "No tasks found", "tasks": []}

            task_list = [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "identifier": t.identifier,
                    "description": t.description[:200] + "..." if t.description and len(t.description) > 200 else t.description,
                }
                for t in tasks
            ]

            return {
                "message": f"Found {len(tasks)} task(s)",
                "tasks": task_list,
            }
        except Exception as e:
            return {"error": f"Failed to list tasks: {str(e)}"}

    async def _get_task(self, kwargs: dict) -> dict:
        """Get a specific task."""
        issue_id = kwargs.get("issue_id")
        if not issue_id:
            return {"error": "issue_id is required"}

        try:
            task = await self.client.get_issue(issue_id)

            return {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "identifier": task.identifier,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "origin_kind": task.origin_kind,
            }
        except Exception as e:
            return {"error": f"Failed to get task: {str(e)}"}

    async def _update_task(self, kwargs: dict) -> dict:
        """Update a task's status or other fields."""
        issue_id = kwargs.get("issue_id")
        if not issue_id:
            return {"error": "issue_id is required"}

        try:
            request = UpdateIssueRequest(
                status=kwargs.get("new_status"),
                priority=kwargs.get("priority"),
                description=kwargs.get("description"),
                title=kwargs.get("title"),
            )

            if not any([request.status, request.priority, request.description, request.title]):
                return {"error": "At least one field to update is required"}

            task = await self.client.update_issue(issue_id, request)

            return {
                "message": "Task updated successfully",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                }
            }
        except Exception as e:
            return {"error": f"Failed to update task: {str(e)}"}

    async def _add_comment(self, kwargs: dict) -> dict:
        """Add a comment to a task."""
        issue_id = kwargs.get("issue_id")
        comment = kwargs.get("comment")

        if not issue_id:
            return {"error": "issue_id is required"}
        if not comment:
            return {"error": "comment is required"}

        try:
            result = await self.client.add_comment(
                issue_id=issue_id,
                body=comment,
                author_agent_id=self.client.agent_id,
            )

            return {
                "message": "Comment added successfully",
                "comment": {
                    "id": result.id,
                    "body": result.body[:100] + "..." if len(result.body) > 100 else result.body,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                }
            }
        except Exception as e:
            return {"error": f"Failed to add comment: {str(e)}"}

    async def _create_task(self, kwargs: dict) -> dict:
        """Create a new task."""
        title = kwargs.get("title")
        if not title:
            return {"error": "title is required for creating a task"}

        try:
            request = CreateIssueRequest(
                title=title,
                description=kwargs.get("description"),
                status=kwargs.get("status", "todo"),
                priority=kwargs.get("priority", "medium"),
                project_id=kwargs.get("project_id"),
                assignee_agent_id=self.client.agent_id,
            )

            task = await self.client.create_issue(request)

            return {
                "message": "Task created successfully",
                "task": {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "identifier": task.identifier,
                }
            }
        except Exception as e:
            return {"error": f"Failed to create task: {str(e)}"}

    async def _fetch_my_tasks(self) -> dict:
        """Fetch tasks assigned to this agent."""
        try:
            tasks = await self.client.get_todo_tasks()

            if not tasks:
                return {"message": "No tasks assigned to you", "tasks": []}

            task_list = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description[:200] + "..." if t.description and len(t.description) > 200 else t.description,
                    "priority": t.priority,
                    "identifier": t.identifier,
                }
                for t in tasks
            ]

            return {
                "message": f"You have {len(tasks)} task(s) assigned",
                "tasks": task_list,
            }
        except Exception as e:
            return {"error": f"Failed to fetch tasks: {str(e)}"}

    async def close(self) -> None:
        """Close the client connection."""
        await self.client.close()
