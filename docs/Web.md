# Web

The web module provides the FastAPI web dashboard for nanobot.

## Files

| File | Description |
|------|-------------|
| `web/__init__.py` | Module initialization |
| `web/api.py` | FastAPI application and server |
| `web/routes.py` | API routes |

---

## API

**File:** `web/api.py`

### StatusResponse

Response schema for status endpoint.

| Field | Type | Description |
|-------|------|-------------|
| `model` | str | Current model |
| `provider` | str | Provider name |
| `workspace` | str | Workspace path |
| `channels_enabled` | list[str] | Enabled channels |
| `cron_jobs` | int | Number of cron jobs |
| `uptime_seconds` | float | Bot uptime |

### SessionInfo

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Session key |
| `created_at` | datetime | Creation time |
| `updated_at` | datetime | Last update |

### MessageInfo

| Field | Type | Description |
|-------|------|-------------|
| `role` | str | Message role |
| `content` | str | Message content |
| `timestamp` | datetime | Message timestamp |

### SessionDetail

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Session key |
| `messages` | list[MessageInfo] | Session messages |
| `created_at` | datetime | Creation time |
| `updated_at` | datetime | Last update |

### Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `create_app` | config, session_manager, cron_service, channels, start_time | FastAPI | Create and configure FastAPI app |
| `run_server` | config, session_manager, cron_service, channels, host, port | None | Run uvicorn server |
| `get_uptime_seconds` | start_time | float | Calculate uptime |

---

## Routes

**File:** `web/routes.py`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | Get agent status |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/{key}` | GET | Get session details |
| `/api/sessions/{key}` | DELETE | Clear a session |
| `/api/cron/jobs` | GET | List cron jobs |
| `/api/config` | GET | Get configuration |
| `/api/ws/events` | WebSocket | Real-time events |

### Paperclip Routes

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/paperclip/tasks` | GET | List tasks |
| `/api/paperclip/tasks/{issue_id}` | GET | Get task details |
| `/api/paperclip/tasks/{issue_id}/complete` | POST | Mark task complete |
| `/api/paperclip/tasks/{issue_id}/comment` | POST | Add comment |
| `/api/paperclip/my-tasks` | GET | Get agent's tasks |

### Dashboard

The web module includes an embedded HTML dashboard with:
- Status view (model, provider, workspace, channels, cron, uptime)
- Sessions list view
- Settings view (configuration)
- WebSocket support for real-time updates

---

## Usage

```bash
# Start web dashboard
nanobot serve --host 0.0.0.0 --port 18791
```

Default URL: http://127.0.0.1:18791
