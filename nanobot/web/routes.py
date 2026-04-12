"""API routes for nanobot web interface."""

import time
from typing import Any

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api")


@router.get("/status")
async def get_status(request: Request) -> dict[str, Any]:
    """Get current agent status."""
    config = request.app.state.config
    cron = request.app.state.cron
    channels = request.app.state.channels
    start_time = request.app.state.start_time

    enabled_channels = []
    if channels and hasattr(channels, 'enabled_channels'):
        enabled_channels = list(channels.enabled_channels)

    cron_jobs = 0
    if cron and hasattr(cron, 'jobs'):
        cron_jobs = len(cron.jobs) if hasattr(cron.jobs, '__len__') else 0
    elif cron and hasattr(cron, 'list_jobs'):
        try:
            cron_jobs = len(cron.list_jobs())
        except Exception:
            cron_jobs = 0

    return {
        "model": config.agents.defaults.model if config else "Unknown",
        "provider": config.get_provider_name() if config else "unknown",
        "workspace": str(config.workspace_path) if config else "N/A",
        "channels_enabled": enabled_channels,
        "cron_jobs": cron_jobs,
        "uptime_seconds": time.time() - start_time if start_time else 0.0,
    }


@router.get("/sessions")
async def list_sessions(request: Request) -> list[dict[str, Any]]:
    """List all sessions."""
    sm = request.app.state.session_manager
    if not sm:
        return []

    sessions = []
    try:
        sessions = sm.list_sessions()
    except Exception:
        pass

    return [
        {
            "key": s.get("key", ""),
            "created_at": s.get("created_at", ""),
            "updated_at": s.get("updated_at", ""),
        }
        for s in sessions
    ]


@router.get("/sessions/{key:path}")
async def get_session(key: str, request: Request) -> dict[str, Any]:
    """Get session details with messages."""
    sm = request.app.state.session_manager
    if not sm:
        return {"key": key, "messages": [], "created_at": "", "updated_at": ""}

    session = None
    try:
        session = sm.get_or_create(key)
    except Exception:
        return {"key": key, "messages": [], "created_at": "", "updated_at": ""}

    return {
        "key": session.key,
        "messages": session.messages,
        "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
        "updated_at": session.updated_at.isoformat() if hasattr(session.updated_at, 'isoformat') else str(session.updated_at),
    }


@router.delete("/sessions/{key:path}")
async def clear_session(key: str, request: Request) -> dict[str, str]:
    """Clear a session."""
    sm = request.app.state.session_manager
    if not sm:
        return {"status": "error", "message": "Session manager not available"}

    try:
        session = sm.get_or_create(key)
        session.clear()
        sm.save(session)
        return {"status": "ok", "message": f"Session '{key}' cleared"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/cron/jobs")
async def list_cron_jobs(request: Request) -> list[dict[str, Any]]:
    """List scheduled cron jobs."""
    cron = request.app.state.cron
    if not cron:
        return []

    try:
        if hasattr(cron, 'list_jobs'):
            return cron.list_jobs()
        if hasattr(cron, 'jobs'):
            return list(cron.jobs.values()) if hasattr(cron.jobs, 'values') else []
    except Exception:
        pass

    return []


@router.get("/config")
async def get_config(request: Request) -> dict[str, Any]:
    """Get current configuration (non-sensitive fields only)."""
    config = request.app.state.config
    if not config:
        return {}

    result = {
        "model": None,
        "provider": None,
        "timezone": "UTC",
        "workspace": None,
        "channels": {},
    }

    try:
        if hasattr(config, 'agents') and hasattr(config.agents, 'defaults'):
            defaults = config.agents.defaults
            result["model"] = getattr(defaults, 'model', None)
            result["provider"] = getattr(defaults, 'provider', None)
            result["timezone"] = getattr(defaults, 'timezone', 'UTC')
    except Exception:
        pass

    try:
        if config and hasattr(config, 'workspace_path'):
            result["workspace"] = str(config.workspace_path)
    except Exception:
        pass

    try:
        if hasattr(config, 'channels'):
            channels = config.channels
            if channels:
                channel_data = channels.model_dump() if hasattr(channels, 'model_dump') else {}
                sensitive_patterns = ['token', 'password', 'secret', 'api_key', 'apikey', 'appsecret', 'clientsecret',
                                      'accesstoken', 'webhook', 'encryptkey', 'verification', 'imap', 'smtp',
                                      'cookie', 'auth', 'bottoken']

                for key, val in channel_data.items():
                    if key.startswith('_'):
                        continue
                    if callable(val):
                        continue

                    if isinstance(val, dict):
                        filtered_val = {}
                        for sub_key, sub_val in val.items():
                            sub_key_lower = sub_key.lower()
                            if any(pattern in sub_key_lower for pattern in sensitive_patterns):
                                if isinstance(sub_val, str) and sub_val:
                                    filtered_val[sub_key] = "[REDACTED]"
                                else:
                                    filtered_val[sub_key] = "[REDACTED]"
                            else:
                                filtered_val[sub_key] = sub_val
                                if sub_key == 'enabled':
                                    pass
                        result["channels"][key] = filtered_val
                    elif isinstance(val, bool):
                        result["channels"][key] = {"enabled": val}
                    else:
                        result["channels"][key] = val
    except Exception:
        pass

    return result


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for real-time events."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": "pong",
                "data": data,
                "timestamp": time.time(),
            })
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


# ============================================================================
# Paperclip Task Routes
# ============================================================================

paperclip_router = APIRouter(prefix="/api/paperclip")


def _get_paperclip_client(request: Request):
    """Get Paperclip client from app state or create from config."""
    config = request.app.state.config
    if not config:
        return None

    pc_config = getattr(config.tools, 'paperclip', None)
    if not pc_config:
        return None

    from nanobot.paperclip.client import PaperclipClient
    return PaperclipClient(
        api_url=pc_config.api_url,
        company_id=pc_config.company_id,
        agent_id=pc_config.agent_id,
    )


@paperclip_router.get("/tasks")
async def list_paperclip_tasks(
    request: Request,
    status: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    """List tasks from Paperclip."""
    client = _get_paperclip_client(request)
    if not client:
        return {"error": "Paperclip not configured"}

    try:
        tasks = await client.list_issues(status=status, priority=priority)
        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "status": t.status,
                    "priority": t.priority,
                    "identifier": t.identifier,
                    "description": t.description,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "updated_at": t.updated_at.isoformat() if t.updated_at else None,
                }
                for t in tasks
            ],
            "count": len(tasks),
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()


@paperclip_router.get("/tasks/{issue_id}")
async def get_paperclip_task(issue_id: str, request: Request) -> dict[str, Any]:
    """Get a specific Paperclip task."""
    client = _get_paperclip_client(request)
    if not client:
        return {"error": "Paperclip not configured"}

    try:
        task = await client.get_issue(issue_id)
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
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()


@paperclip_router.post("/tasks/{issue_id}/complete")
async def complete_paperclip_task(
    issue_id: str,
    request: Request,
    comment: str | None = None,
) -> dict[str, Any]:
    """Mark a Paperclip task as completed."""
    client = _get_paperclip_client(request)
    if not client:
        return {"error": "Paperclip not configured"}

    try:
        if comment:
            await client.add_comment(
                issue_id=issue_id,
                body=comment,
                author_agent_id=client.agent_id,
            )
        task = await client.complete_issue(issue_id)
        return {
            "status": "ok",
            "message": f"Task {task.identifier or issue_id} completed",
            "task": {
                "id": task.id,
                "status": task.status,
            },
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()


@paperclip_router.post("/tasks/{issue_id}/comment")
async def add_paperclip_comment(
    issue_id: str,
    request: Request,
    body: str,
) -> dict[str, Any]:
    """Add a comment to a Paperclip task."""
    client = _get_paperclip_client(request)
    if not client:
        return {"error": "Paperclip not configured"}

    try:
        comment = await client.add_comment(
            issue_id=issue_id,
            body=body,
            author_agent_id=client.agent_id,
        )
        return {
            "status": "ok",
            "comment": {
                "id": comment.id,
                "body": comment.body,
                "created_at": comment.created_at.isoformat() if comment.created_at else None,
            },
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()


@paperclip_router.get("/my-tasks")
async def get_my_tasks(request: Request) -> dict[str, Any]:
    """Get tasks assigned to this agent."""
    client = _get_paperclip_client(request)
    if not client:
        return {"error": "Paperclip not configured"}

    try:
        tasks = await client.get_todo_tasks()
        return {
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "priority": t.priority,
                    "identifier": t.identifier,
                }
                for t in tasks
            ],
            "count": len(tasks),
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        await client.close()


# Register paperclip router in main app
def register_paperclip_routes(app):
    app.include_router(paperclip_router)


# ============================================================================
# Subagents Routes
# ============================================================================

@router.get("/subagents")
async def list_subagents(request: Request) -> list[dict[str, Any]]:
    """List all configured subagents."""
    workspace = request.app.state.config.workspace_path if request.app.state.config else None
    if not workspace:
        return []

    import json
    subagent_dir = workspace / ".subagents"
    if not subagent_dir.exists():
        return []

    subagents = []
    for config_file in subagent_dir.glob("*.json"):
        if config_file.name == "config.json":
            continue
        try:
            cfg = json.loads(config_file.read_text(encoding="utf-8"))
            subagents.append({
                "id": config_file.stem,
                "role": cfg.get("role", ""),
                "enabled": cfg.get("enabled", False),
                "bot_username": cfg.get("bot_username", ""),
                "model": cfg.get("model", ""),
                "heartbeat_enabled": cfg.get("heartbeat", {}).get("enabled", False),
                "heartbeat_task": cfg.get("heartbeat", {}).get("task", ""),
            })
        except Exception:
            pass

    return subagents


# ============================================================================
# File Browser Routes
# ============================================================================

@router.get("/files")
async def list_files(request: Request, path: str = "") -> dict[str, Any]:
    """List files in workspace."""
    workspace = request.app.state.config.workspace_path if request.app.state.config else None
    if not workspace:
        return {"error": "No workspace"}

    target_path = (workspace / path) if path else workspace

    if not target_path.exists():
        return {"error": "Path not found"}

    if target_path.is_file():
        # Return file content
        content = target_path.read_text(encoding="utf-8")
        return {
            "type": "file",
            "name": target_path.name,
            "path": str(target_path.relative_to(workspace)),
            "content": content,
        }

    # Return directory contents
    items = []
    for item in sorted(target_path.iterdir()):
        # Include all files including hidden ones
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "path": str(item.relative_to(workspace)),
            "hidden": item.name.startswith("."),
        })

    return {"type": "directory", "items": items}


@router.get("/files/{file_path:path}")
async def read_file(request: Request, file_path: str) -> dict[str, Any]:
    """Read a specific file."""
    workspace = request.app.state.config.workspace_path if request.app.state.config else None
    if not workspace:
        return {"error": "No workspace"}

    target_path = workspace / file_path
    if not target_path.exists() or not target_path.is_file():
        return {"error": "File not found"}

    content = target_path.read_text(encoding="utf-8")
    return {
        "name": target_path.name,
        "path": file_path,
        "content": content,
    }


@router.put("/files/{file_path:path}")
async def save_file(request: Request, file_path: str) -> dict[str, str]:
    """Save a file."""
    workspace = request.app.state.config.workspace_path if request.app.state.config else None
    if not workspace:
        return {"status": "error", "message": "No workspace"}

    target_path = workspace / file_path
    if not target_path.exists():
        return {"status": "error", "message": "File not found"}

    try:
        body = await request.body()
        content = body.decode("utf-8")
        target_path.write_text(content, encoding="utf-8")
        return {"status": "ok", "message": "File saved"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
