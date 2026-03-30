# Paperclip

The paperclip module provides integration with the Paperclip task management system. It includes a client for the Paperclip API, models for the data structures, a CLI for interactions, and a poller for background task synchronization.

## Files

| File | Description |
|------|-------------|
| `paperclip/__init__.py` | Module initialization |
| `paperclip/client.py` | Paperclip API client |
| `paperclip/models.py` | Pydantic models for Paperclip data |
| `paperclip/cli.py` | CLI commands for Paperclip |
| `paperclip/poller.py` | Background poller for task synchronization |

---

## Client

**File:** `paperclip/client.py`

### PaperclipClient

HTTP client for interacting with the Paperclip API.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | api_url, company_id, agent_id, api_key | - | Initialize the client |
| `get_tasks` | status, priority, project_id, limit | list[Task] | Fetch tasks with optional filters |
| `get_task` | issue_id | Task | Get a specific task by ID |
| `create_task` | title, description, priority, project_id | Task | Create a new task |
| `update_task` | issue_id, status, priority, title, description | Task | Update an existing task |
| `add_comment` | issue_id, body | Comment | Add a comment to a task |
| `get_my_tasks` | - | list[Task] | Get tasks assigned to the current agent |

---

## Models

**File:** `paperclip/models.py`

### Task

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Task ID |
| `issue_id` | str | Public issue identifier |
| `title` | str | Task title |
| `description` | str | Task description |
| `status` | str | Task status |
| `priority` | str | Task priority |
| `assignee_id` | int | Assigned user ID |
| `reporter_id` | int | Reporter user ID |
| `project_id` | int | Project ID |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `due_date` | datetime | Due date (optional) |

### Comment

| Field | Type | Description |
|-------|------|-------------|
| `id` | int | Comment ID |
| `issue_id` | str | Associated task ID |
| `body` | str | Comment content |
| `author_id` | int | Author user ID |
| `created_at` | datetime | Creation timestamp |

---

## CLI

**File:** `paperclip/cli.py`

### Commands

| Command | Description |
|---------|-------------|
| `tasks` | List tasks with optional filtering |
| `task <issue_id>` | Show details of a specific task |
| `create` | Create a new task |
| `update <issue_id>` | Update a task |
| `comment <issue_id>` | Add a comment to a task |
| `my-tasks` | Show tasks assigned to current agent |

---

## Poller

**File:** `paperclip/poller.py`

### PaperclipPoller

Background service that periodically polls Paperclip for new tasks assigned to the agent.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | client, bus, poll_interval | - | Initialize the poller |
| `start` | - | None | Start polling in background |
| `stop` | - | None | Stop the poller |
| `_poll_loop` | - | None | Main polling loop |
| `_check_new_tasks` | - | None | Check for new tasks and publish to bus |

#### Configuration
- `poll_interval`: How often to poll (default: 60 seconds)
- `bus`: Message bus for publishing new task events

---

## Usage

The agent can interact with Paperclip through:
1. **PaperclipTool** - Available as a tool in agent context
2. **CLI commands** - Direct CLI access
3. **Poller** - Background synchronization of assigned tasks
