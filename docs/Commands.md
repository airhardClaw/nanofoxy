# Commands

The command module handles command routing and builtin commands for nanobot.

## Files

| File | Description |
|------|-------------|
| `command/__init__.py` | Module initialization |
| `command/router.py` | Command routing logic |
| `command/builtin.py` | Builtin command implementations |

---

## Router

**File:** `command/router.py`

### CommandRouter

Routes messages to appropriate command handlers.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | bus, agent | - | Initialize with message bus and agent |
| `route` | message | None | Route a message to appropriate handler |
| `register_command` | name, handler | None | Register a custom command |
| `_parse_command` | text | tuple | Parse command name and arguments |

### Command Pattern
Commands are prefixed with `/` (e.g., `/help`, `/status`)

---

## Builtin Commands

**File:** `command/builtin.py`

### Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show agent status |
| `/clear` | Clear conversation history |
| `/skills` | List available skills |
| `/version` | Show nanobot version |
| `/memory` | Query agent memory |

### Command Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `help_command` | message, args | str | Show help text |
| `status_command` | message, args | str | Show agent status |
| `clear_command` | message, args | str | Clear session history |
| `skills_command` | message, args | str | List skills |
| `version_command` | message, args | str | Show version |
| `memory_command` | message, args | str | Query memory |

---

## Command Execution Flow

```
Incoming Message
       │
       ▼
CommandRouter.route()
       │
       ▼
_parse_command() ──▶ Extract /command and args
       │
       ▼
Find Handler (builtin or custom)
       │
       ▼
Execute Handler
       │
       ▼
Return Response
```
