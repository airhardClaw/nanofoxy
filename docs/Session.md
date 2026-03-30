# Session

The session module manages conversation sessions for nanobot.

## Files

| File | Description |
|------|-------------|
| `session/__init__.py` | Module initialization |
| `session/manager.py` | Session manager implementation |

---

## Manager

**File:** `session/manager.py`

### SessionManager

Manages conversation sessions across different chats/users.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace, max_history | - | Initialize session manager |
| `get_or_create` | channel, chat_id | Session | Get or create a session |
| `get` | key | Session | Get a session by key |
| `delete` | key | None | Delete a session |
| `list` | - | list[Session] | List all sessions |
| `cleanup` | - | None | Clean up old sessions |

### Session

| Field | Type | Description |
|-------|------|-------------|
| `key` | str | Unique session key (channel:chat_id) |
| `channel` | str | Channel name |
| `chat_id` | str | Chat/user ID |
| `messages` | list[dict] | Message history |
| `created_at` | datetime | Creation timestamp |
| `updated_at` | datetime | Last update timestamp |
| `metadata` | dict | Session metadata |

### Session Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `add_message` | role, content | None | Add a message to history |
| `add_tool_call` | call_id, name, args | None | Add a tool call |
| `add_tool_result` | call_id, result | None | Add a tool result |
| `get_messages` | - | list[dict] | Get all messages |
| `clear` | - | None | Clear session history |
| `truncate` | max_messages | None | Truncate history to max messages |

---

## Session Key Format

```
{channel}:{chat_id}
```

Example: `telegram:123456789`

---

## Configuration

| Setting | Description | Default |
|---------|-------------|---------|
| `max_history` | Maximum messages to keep in history | 50 |
| `ttl` | Session time-to-live in seconds | 86400 (24 hours) |
| `persist_path` | Where to persist sessions | `{workspace}/sessions.json` |
