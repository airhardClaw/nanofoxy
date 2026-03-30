# Cron

The cron module handles scheduled task execution for nanobot.

## Files

| File | Description |
|------|-------------|
| `cron/__init__.py` | Module initialization |
| `cron/service.py` | Cron job service implementation |
| `cron/types.py` | Cron job type definitions |

---

## Service

**File:** `cron/service.py`

### CronService

Manages scheduled jobs and their execution.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | bus, agent, channels | - | Initialize cron service |
| `start` | - | None | Start the cron scheduler |
| `stop` | - | None | Stop the cron scheduler |
| `add_job` | job | str | Add a new job, returns job_id |
| `remove_job` | job_id | None | Remove a job |
| `list_jobs` | - | list[dict] | List all scheduled jobs |
| `_run_job` | job | None | Execute a job |

---

## Types

**File:** `cron/types.py`

### CronJob

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Unique job identifier |
| `type` | str | Job type: message, agent, tool |
| `schedule` | dict | Schedule configuration |
| `action` | dict | Action to perform |
| `channel` | str | Target channel |
| `chat_id` | str | Target chat ID |
| `enabled` | bool | Whether job is enabled |
| `next_run` | datetime | Next scheduled run |

### Schedule Types

| Type | Description | Example |
|------|-------------|---------|
| `interval` | Run every N seconds | `{"every_seconds": 60}` |
| `cron` | Cron expression | `{"cron_expr": "0 9 * * *"}` |
| `once` | Run once at specific time | `{"at": "2024-01-01T09:00:00Z"}` |

### Job Types

| Type | Description |
|------|-------------|
| `message` | Send a message |
| `agent` | Run an agent task |
| `tool` | Execute a tool |

---

## Usage

Jobs can be added via:
1. **CronTool** - Agent can add/remove/list cron jobs
2. **API** - Via web dashboard
3. **Config** - Pre-configured jobs in config file

### Example: Add a Reminder

```
Agent: /cron add --message "Take a break!" --every 3600
```

This creates a job that runs every hour (3600 seconds).
