"""Paperclip API client for nanobot."""

import httpx
from datetime import datetime
from typing import Optional

from nanobot.paperclip.models import (
    Issue,
    IssueComment,
    CreateIssueRequest,
    UpdateIssueRequest,
    Company,
)


class PaperclipClient:
    """Client for interacting with Paperclip API."""
    
    def __init__(
        self,
        api_url: str = "http://127.0.0.1:3100",
        company_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.company_id = company_id
        self.agent_id = agent_id
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
    
    def _get_headers(self) -> dict:
        """Get headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def list_companies(self) -> list[Company]:
        """List all companies."""
        response = await self._client.get(
            f"{self.api_url}/api/companies",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        data = response.json()
        return [Company(**c) for c in data]
    
    async def list_issues(
        self,
        status: Optional[str] = None,
        assignee_agent_id: Optional[str] = None,
        project_id: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 50,
    ) -> list[Issue]:
        """List issues with optional filters."""
        if not self.company_id:
            raise ValueError("company_id is required")
        
        params = {"limit": limit}
        if status:
            params["status"] = status
        if assignee_agent_id:
            params["assignee_agent_id"] = assignee_agent_id
        if project_id:
            params["project_id"] = project_id
        if priority:
            params["priority"] = priority
        
        response = await self._client.get(
            f"{self.api_url}/api/companies/{self.company_id}/issues",
            params=params,
            headers=self._get_headers(),
        )
        response.raise_for_status()
        data = response.json()
        
        items = data if isinstance(data, list) else data.get("items", [])
        return [Issue(**issue) for issue in items]
    
    async def get_issue(self, issue_ref: str) -> Issue:
        """Get a single issue by ID (UUID or identifier like 'NANAA-10')."""
        import re
        is_uuid = bool(re.match(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
            issue_ref,
            re.IGNORECASE
        ))
        
        try:
            response = await self._client.get(
                f"{self.api_url}/api/issues/{issue_ref}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return Issue(**response.json())
        except httpx.HTTPStatusError:
            pass
        
        issues = await self.list_issues(limit=100)
        issue_ref_lower = issue_ref.lower()
        for issue in issues:
            if issue.identifier and issue.identifier.lower() == issue_ref_lower:
                return issue
        
        raise ValueError(f"Issue not found: {issue_ref}")
    
    async def create_issue(self, request: CreateIssueRequest) -> Issue:
        """Create a new issue."""
        if not self.company_id:
            raise ValueError("company_id is required")
        
        response = await self._client.post(
            f"{self.api_url}/api/companies/{self.company_id}/issues",
            json=request.model_dump(mode="json", exclude_none=True),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return Issue(**response.json())
    
    async def update_issue(self, issue_id: str, request: UpdateIssueRequest) -> Issue:
        """Update an existing issue."""
        response = await self._client.patch(
            f"{self.api_url}/api/issues/{issue_id}",
            json=request.model_dump(mode="json", exclude_none=True),
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return Issue(**response.json())
    
    async def claim_issue(self, issue_id: str) -> Issue:
        """Claim an issue (set status to in_progress and lock it)."""
        return await self.update_issue(
            issue_id,
            UpdateIssueRequest(
                status="in_progress",
                started_at=datetime.utcnow(),
            )
        )
    
    async def release_issue(self, issue_id: str) -> Issue:
        """Release a claimed issue (set status back to todo)."""
        return await self.update_issue(
            issue_id,
            UpdateIssueRequest(
                status="todo",
                started_at=None,
            )
        )
    
    async def complete_issue(self, issue_id: str) -> Issue:
        """Mark an issue as completed."""
        return await self.update_issue(
            issue_id,
            UpdateIssueRequest(
                status="done",
                completed_at=datetime.utcnow(),
            )
        )
    
    async def list_comments(self, issue_id: str) -> list[IssueComment]:
        """List comments on an issue."""
        response = await self._client.get(
            f"{self.api_url}/api/issues/{issue_id}/comments",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        data = response.json()
        items = data if isinstance(data, list) else data.get("items", [])
        return [IssueComment(**comment) for comment in items]
    
    async def add_comment(
        self,
        issue_id: str,
        body: str,
        author_agent_id: Optional[str] = None,
    ) -> IssueComment:
        """Add a comment to an issue."""
        payload = {"body": body}
        if author_agent_id:
            payload["author_agent_id"] = author_agent_id
        
        response = await self._client.post(
            f"{self.api_url}/api/issues/{issue_id}/comments",
            json=payload,
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return IssueComment(**response.json())
    
    async def get_todo_tasks(self) -> list[Issue]:
        """Get all todo tasks assigned to this agent."""
        return await self.list_issues(
            status="todo",
            assignee_agent_id=self.agent_id,
        )
    
    async def get_in_progress_tasks(self) -> list[Issue]:
        """Get all in-progress tasks assigned to this agent."""
        return await self.list_issues(
            status="in_progress",
            assignee_agent_id=self.agent_id,
        )
