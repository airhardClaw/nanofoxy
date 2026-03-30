# Heartbeat

The heartbeat module provides a health check service for nanobot.

## Files

| File | Description |
|------|-------------|
| `heartbeat/__init__.py` | Module initialization |
| `heartbeat/service.py` | Heartbeat service implementation |

---

## Service

**File:** `heartbeat/service.py`

### HeartbeatService

Runs periodic background tasks to check the agent's health and perform maintenance.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace, agent | - | Initialize heartbeat service |
| `start` | - | None | Start the heartbeat loop |
| `stop` | - | None | Stop the heartbeat |
| `_heartbeat_loop` | - | None | Main heartbeat loop |
| `_check_health` | - | None | Perform health check |
| `_check_heartbeat_file` | - | None | Check HEARTBEAT.md for tasks |

---

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `interval` | Heartbeat interval in seconds | 60 |
| `enabled` | Whether heartbeat is enabled | true |

---

## HEARTBEAT.md

The agent checks for a `HEARTBEAT.md` file in the workspace for periodic tasks.

### Format

```markdown
# Heartbeat Tasks

## Every hour
- Check disk space
- Clean up old logs

## Every day
- Backup memory
- Review session history
```

The agent will interpret these tasks and execute them at the appropriate intervals.
