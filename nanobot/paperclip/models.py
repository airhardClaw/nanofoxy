"""Pydantic models for Paperclip API."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class Issue(BaseModel):
    """Represents a Paperclip issue/task."""
    
    id: str
    company_id: Optional[str] = None
    project_id: Optional[str] = None
    goal_id: Optional[str] = None
    parent_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = "backlog"
    priority: str = "medium"
    assignee_agent_id: Optional[str] = None
    assignee_user_id: Optional[str] = None
    created_by_agent_id: Optional[str] = None
    created_by_user_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    issue_number: Optional[int] = None
    identifier: Optional[str] = None
    origin_kind: str = "manual"
    origin_id: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @property
    def is_todo(self) -> bool:
        return self.status == "todo"
    
    @property
    def is_in_progress(self) -> bool:
        return self.status == "in_progress"
    
    @property
    def is_done(self) -> bool:
        return self.status in ("done", "completed")
    
    def to_summary(self) -> str:
        """Return a short summary of the issue."""
        return f"[{self.identifier or self.id[:8]}] {self.title} ({self.status})"


class IssueComment(BaseModel):
    """Represents a comment on an issue."""
    
    id: str
    company_id: str = Field(alias="companyId", default="")
    issue_id: str = Field(alias="issueId", default="")
    author_agent_id: Optional[str] = Field(default=None, alias="authorAgentId")
    author_user_id: Optional[str] = Field(default=None, alias="authorUserId")
    body: str
    created_at: Optional[datetime] = Field(default=None, alias="createdAt")
    updated_at: Optional[datetime] = Field(default=None, alias="updatedAt")
    
    model_config = ConfigDict(populate_by_name=True)


class IssueListResponse(BaseModel):
    """Response when listing issues."""
    
    items: list[Issue] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class CreateIssueRequest(BaseModel):
    """Request to create a new issue."""
    
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    project_id: Optional[str] = None
    assignee_agent_id: Optional[str] = None
    assignee_user_id: Optional[str] = None


class UpdateIssueRequest(BaseModel):
    """Request to update an issue."""
    
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Company(BaseModel):
    """Represents a Paperclip company."""
    
    id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    issue_prefix: Optional[str] = None
    issue_counter: int = 0
    
    class Config:
        from_attributes = True


class Project(BaseModel):
    """Represents a Paperclip project."""
    
    id: str
    company_id: str
    name: str
    description: Optional[str] = None
    status: str = "active"
    
    class Config:
        from_attributes = True
