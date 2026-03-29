"""Paperclip CLI commands for nanobot."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown

from nanobot.paperclip.client import PaperclipClient
from nanobot.paperclip.models import CreateIssueRequest

paperclip_app = typer.Typer(
    name="paperclip",
    help="Manage Paperclip tasks and issues",
)

console = Console()


def _get_paperclip_config() -> dict:
    """Load Paperclip config from nanobot config."""
    from nanobot.config.loader import load_config
    
    config = load_config()
    
    pc_dict = {
        "api_url": "http://127.0.0.1:3100",
        "company_id": "",
        "agent_id": "",
    }
    
    if hasattr(config, 'tools') and hasattr(config.tools, 'paperclip'):
        pc = config.tools.paperclip
        pc_dict["api_url"] = pc.api_url
        pc_dict["company_id"] = pc.company_id
        pc_dict["agent_id"] = pc.agent_id
    
    return pc_dict


def _create_client(pc_dict: dict) -> PaperclipClient:
    """Create a Paperclip client from config dict."""
    return PaperclipClient(
        api_url=pc_dict.get("api_url", "http://127.0.0.1:3100"),
        company_id=pc_dict.get("company_id", ""),
        agent_id=pc_dict.get("agent_id", ""),
    )


@paperclip_app.command("list")
def list_tasks(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
):
    """List tasks from Paperclip."""
    pc_dict = _get_paperclip_config()
    
    if not pc_dict["company_id"]:
        console.print("[yellow]Warning: company_id not configured[/yellow]")
        console.print("[dim]Set tools.paperclip.company_id in your config[/dim]")
        return
    
    client = _create_client(pc_dict)
    
    try:
        tasks = asyncio.get_event_loop().run_until_complete(
            client.list_issues(status=status, priority=priority, limit=limit)
        )
        
        if not tasks:
            console.print("[yellow]No tasks found[/yellow]")
            return
        
        table = Table(title=f"Tasks ({len(tasks)} found)")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Title", style="white")
        table.add_column("Status", style="yellow")
        table.add_column("Priority", style="magenta")
        
        for task in tasks:
            table.add_row(
                task.identifier or task.id[:8],
                task.title[:50] + "..." if len(task.title) > 50 else task.title,
                task.status,
                task.priority,
            )
        
        console.print(table)
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


@paperclip_app.command("fetch")
def fetch_tasks():
    """Fetch tasks assigned to this agent."""
    pc_dict = _get_paperclip_config()
    
    if not pc_dict.get("agent_id"):
        console.print("[yellow]Warning: agent_id not configured[/yellow]")
    
    client = _create_client(pc_dict)
    
    try:
        tasks = asyncio.get_event_loop().run_until_complete(client.get_todo_tasks())
        
        if not tasks:
            console.print("[green]No tasks assigned to you[/green]")
            return
        
        console.print(f"[green]You have {len(tasks)} task(s) assigned:[/green]\n")
        
        for i, task in enumerate(tasks, 1):
            console.print(f"[cyan]{i}. {task.title}[/cyan]")
            if task.description:
                desc = task.description[:100] + "..." if len(task.description) > 100 else task.description
                console.print(f"   {desc}")
            console.print(f"   Priority: {task.priority} | ID: `{task.identifier or task.id[:8]}`")
            console.print()
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


@paperclip_app.command("show")
def show_task(
    issue_id: str = typer.Argument(..., help="Issue ID or identifier"),
):
    """Show details of a specific task."""
    pc_dict = _get_paperclip_config()
    client = _create_client(pc_dict)
    
    try:
        task = asyncio.get_event_loop().run_until_complete(client.get_issue(issue_id))
        
        console.print(f"\n[cyan]## {task.title}[/cyan]")
        console.print(f"**ID:** `{task.id}`")
        console.print(f"**Identifier:** `{task.identifier or 'N/A'}`")
        console.print(f"**Status:** {task.status}")
        console.print(f"**Priority:** {task.priority}")
        
        if task.description:
            console.print("\n**Description:**")
            console.print(Markdown(task.description))
        
        console.print(f"\n**Created:** {task.created_at}")
        console.print(f"**Updated:** {task.updated_at}")
        
        if task.started_at:
            console.print(f"**Started:** {task.started_at}")
        if task.completed_at:
            console.print(f"**Completed:** {task.completed_at}")
        
        try:
            comments = asyncio.get_event_loop().run_until_complete(client.list_comments(task.id))
            if comments:
                console.print(f"\n**Comments ({len(comments)}):**")
                for comment in comments:
                    author = comment.author_agent_id or comment.author_user_id or "Unknown"
                    console.print(f"\n[{comment.created_at}] {author}:")
                    console.print(f"  {comment.body[:200]}...")
        except Exception:
            pass
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


@paperclip_app.command("complete")
def complete_task(
    issue_id: str = typer.Argument(..., help="Issue ID or identifier"),
    comment: Optional[str] = typer.Option(None, "--comment", "-c", help="Completion comment"),
):
    """Mark a task as completed."""
    pc_dict = _get_paperclip_config()
    client = _create_client(pc_dict)
    
    try:
        loop = asyncio.get_event_loop()
        
        task = loop.run_until_complete(client.get_issue(issue_id))
        issue_uuid = task.id
        
        if comment:
            try:
                loop.run_until_complete(
                    client.add_comment(issue_uuid, comment, pc_dict.get("agent_id"))
                )
                console.print("[green]Added comment[/green]")
            except Exception:
                console.print("[yellow]Warning: Could not add comment (endpoint may not exist)[/yellow]")
        
        loop.run_until_complete(client.complete_issue(issue_uuid))
        console.print(f"[green]Marked task {issue_id} as completed[/green]")
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


@paperclip_app.command("update")
def update_task(
    issue_id: str = typer.Argument(..., help="Issue ID or identifier"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New priority"),
):
    """Update task status or priority."""
    if not status and not priority:
        console.print("[red]Error: Either --status or --priority is required[/red]")
        raise typer.Exit(1)
    
    pc_dict = _get_paperclip_config()
    client = _create_client(pc_dict)
    
    try:
        loop = asyncio.get_event_loop()
        task = loop.run_until_complete(client.get_issue(issue_id))
        issue_uuid = task.id
        
        from nanobot.paperclip.models import UpdateIssueRequest
        request = UpdateIssueRequest(status=status, priority=priority)
        
        task = loop.run_until_complete(client.update_issue(issue_uuid, request))
        
        console.print(f"[green]Updated task: {task.title}[/green]")
        console.print(f"  Status: {task.status}")
        console.print(f"  Priority: {task.priority}")
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


@paperclip_app.command("comment")
def add_comment(
    issue_id: str = typer.Argument(..., help="Issue ID or identifier"),
    body: str = typer.Argument(..., help="Comment text"),
):
    """Add a comment to a task."""
    pc_dict = _get_paperclip_config()
    client = _create_client(pc_dict)
    
    try:
        comment = asyncio.get_event_loop().run_until_complete(
            client.add_comment(issue_id, body, pc_dict.get("agent_id"))
        )
        console.print(f"[green]Comment added: {comment.id}[/green]")
    finally:
        asyncio.get_event_loop().run_until_complete(client.close())


if __name__ == "__main__":
    paperclip_app()
