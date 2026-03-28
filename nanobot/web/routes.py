"""API routes for nanobot web interface."""

import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

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
                        has_enabled = False
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
                                    has_enabled = sub_val
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
    request = websocket.app.state

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
