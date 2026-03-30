# Agent Tools

The agent tools module provides the tools that the agent can use to interact with the outside world. It includes a base Tool class, a ToolRegistry for managing tools, and implementations for various functionalities like filesystem operations, shell execution, web search/fetch, memory queries, messaging, cron scheduling, subagent spawning, and MCP server integration.

## Files

| File | Description |
|------|-------------|
| `agent/tools/__init__.py` | Module exports (Tool, ToolRegistry) |
| `agent/tools/base.py` | Abstract base Tool class |
| `agent/tools/registry.py` | Tool registry for dynamic tool management |
| `agent/tools/filesystem.py` | File operations (read, write, edit, list, backup) |
| `agent/tools/shell.py` | Shell command execution |
| `agent/tools/web.py` | Web search and fetch |
| `agent/tools/memory.py` | Query agent memory |
| `agent/tools/message.py` | Send messages to users |
| `agent/tools/cron.py` | Schedule reminders and tasks |
| `agent/tools/spawn.py` | Spawn subagents for background tasks |
| `agent/tools/mcp.py` | MCP server integration |
| `agent/tools/paperclip.py` | Paperclip task management integration |

---

## Classes

### Tool (Abstract Base Class)

**File:** `agent/tools/base.py`

Abstract base class that all tools inherit from. Defines the interface and provides utility methods for parameter validation and type casting.

| Method/Property | Type | Description |
|-----------------|------|-------------|
| `name` | str (abstract) | Tool name used in function calls |
| `description` | str (abstract) | Description of what the tool does |
| `parameters` | dict[str, Any] (abstract) | JSON Schema for tool parameters |
| `execute(**kwargs)` | - | Abstract async method - must be implemented by subclasses |
| `cast_params(params)` | dict | Applies safe schema-driven type casts before validation |
| `validate_params(params)` | list[str] | Validates tool parameters against JSON schema, returns list of error strings |
| `to_schema()` | dict | Converts tool to OpenAI function schema format |

#### Internal Helper Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `_resolve_type` | t | str | Resolves JSON Schema type (handles union types like `["string", "null"]`) |
| `_cast_object` | obj, schema | dict | Casts a dict according to schema |
| `_cast_value` | val, schema | Any | Casts a single value according to schema (handles string→int, string→bool conversions) |
| `_validate` | val, schema, path | list[str] | Recursive validation against JSON schema |

#### Type Map

| JSON Schema Type | Python Type |
|------------------|-------------|
| `string` | str |
| `integer` | int |
| `number` | float |
| `boolean` | bool |
| `array` | list |
| `object` | dict |

---

### ToolRegistry

**File:** `agent/tools/registry.py`

Central registry for dynamic tool management. Allows tools to be registered, unregistered, and executed by name.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `register` | tool | None | Register a tool instance by its name |
| `unregister` | name | None | Unregister a tool by name (silent fail if not found) |
| `get` | name | Tool | Get a tool by name, returns `None` if not found |
| `has` | name | bool | Check if a tool is registered |
| `get_definitions` | - | list[dict] | Get all tool definitions in OpenAI function calling format |
| `execute` | name, params | Any | Execute a tool by name with given parameters (async) |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `tool_names` | list[str] | List of registered tool names |
| `__len__` | int | Number of registered tools |
| `__contains__(name)` | bool | Membership check |

#### Execution Flow

1. Looks up tool by name
2. Casts parameters to match schema types
3. Validates parameters against schema
4. Calls `tool.execute(**params)`
5. Appends hint message on errors: `"\n\n[Analyze the error above and try a different approach.]"`

---

### MemoryTool

**File:** `agent/tools/memory.py`

Query and search agent's long-term memory.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"memory"` |
| `description` | str | Query and search agent's long-term memory |
| `parameters` | dict | JSON Schema for action, query |

#### Constructor

```python
def __init__(self, workspace: Path | None = None)
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string (enum: search/summary/history) | Action to perform (required) |
| `query` | string | Search query (required for search/history) |

#### Actions

| Action | Description |
|--------|-------------|
| `search` | Search memory for specific information |
| `summary` | Get a brief overview of memory |
| `history` | Search recent events in memory |

---

## Filesystem Tools

**File:** `agent/tools/filesystem.py`

### Helper Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_resolve_path` | path, workspace, allowed_dir, extra_allowed_dirs | Path | Resolve path against workspace and enforce directory restrictions |
| `_is_under` | path, directory | bool | Check if path is under a directory |
| `_find_match` | content, old_text | tuple | Locate text in content with fuzzy matching |

### _FsTool (Base Class)

Base class for all filesystem tools with shared initialization, path resolution, and backup management.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `list_file_backups` | file_path | list | List available backups for a file |
| `_create_file_backup` | file_path | None | Create timestamped backup before write |
| `_cleanup_old_file_backups` | file_path | None | Remove old backups beyond limit |

---

### ReadFileTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"read_file"` |
| `description` | str | Read file contents with optional line-based pagination |
| `parameters` | dict | JSON Schema for path, offset, limit |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path to read |
| `offset` | integer | 1-indexed line to start reading from |
| `limit` | integer | Number of lines to read |

#### Features
- Supports images (converts to text representation)
- Line numbering
- Pagination
- Maximum 128K characters

---

### WriteFileTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"write_file"` |
| `description` | str | Write content to a file |
| `parameters` | dict | JSON Schema for path, content, create_backup |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path to write |
| `content` | string | Content to write |
| `create_backup` | boolean | Whether to create backup (default: true) |

#### Features
- Creates parent directories if they don't exist
- Automatic backups before writing

---

### EditFileTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"edit_file"` |
| `description` | str | Edit file by replacing text with fallback matching |
| `parameters` | dict | JSON Schema for path, old_text, new_text, replace_all |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path to edit |
| `old_text` | string | Text to find and replace |
| `new_text` | string | Text to replace with |
| `replace_all` | boolean | Replace all occurrences (default: false) |

#### Features
- Fuzzy matching when exact text not found
- CRLF handling
- Shows diff for best match

---

### ListDirTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"list_dir"` |
| `description` | str | List directory contents with optional recursion |
| `parameters` | dict | JSON Schema for path, recursive, max_entries |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Directory path to list |
| `recursive` | boolean | List subdirectories (default: false) |
| `max_entries` | integer | Maximum entries to return |

#### Features
- Auto-ignores `.git`, `node_modules`, `__pycache__`, etc.

---

### RestoreFileBackupTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"restore_file_backup"` |
| `description` | str | Restore file from backup |
| `parameters` | dict | JSON Schema for path, timestamp |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | File path to restore |
| `timestamp` | string | Optional specific backup timestamp |

#### Features
- Restores most recent backup if no timestamp specified

---

### ListFileBackupsTool

**File:** `agent/tools/filesystem.py`

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"list_file_backups"` |
| `description` | str | List all available backups for a file |
| `parameters` | dict | JSON Schema for path |

---

## Shell Execution Tool

**File:** `agent/tools/shell.py`

### ExecTool

Execute shell commands with safety guards.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"exec"` |
| `description` | str | Execute a shell command and return its output |
| `parameters` | dict | JSON Schema for command, working_dir, timeout |

#### Constructor

```python
def __init__(self, 
    timeout: int = 60, 
    working_dir: str | None = None, 
    deny_patterns: list[str] | None = None, 
    allow_patterns: list[str] | None = None,
    restrict_to_workspace: bool = False, 
    path_append: str = "")
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `command` | string | Shell command to execute (required) |
| `working_dir` | string | Optional working directory |
| `timeout` | integer | Timeout in seconds (default: 60, max: 600) |

#### Safety Features

**Deny Patterns** - Blocks dangerous commands:
- `rm -rf`
- `format`
- `shutdown`
- `fork bombs`
- And more...

**Allow Patterns** - Optional whitelist approach

**Path Restriction** - Prevents path traversal (`..`)

**Internal URL Detection** - Blocks commands containing internal/private URLs

**Workspace Restriction** - Optionally restricts to working directory

#### Output
- Truncates output to 10,000 chars (head + tail preserved)
- Returns exit code

---

## Web Tools

**File:** `agent/tools/web.py`

### Helper Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_strip_tags` | text | str | Remove HTML tags and decode entities |
| `_normalize` | text | str | Normalize whitespace |
| `_validate_url` | url | tuple[bool, str] | Validate URL scheme/domain |
| `_validate_url_safe` | url | tuple[bool, str] | Validate URL with SSRF protection |
| `_format_results` | query, items, n | str | Format search results into plaintext |

---

### WebSearchTool

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"web_search"` |
| `description` | str | Search the web using configured provider |
| `parameters` | dict | JSON Schema for query, count |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Search query |
| `count` | integer | Number of results (1-10, default: 5) |

#### Supported Providers
- Brave
- Tavily
- SearXNG
- Jina
- DuckDuckGo (fallback)

#### Features
- Automatic fallback on API key failure

---

### WebFetchTool

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"web_fetch"` |
| `description` | str | Fetch URL and extract readable content |
| `parameters` | dict | JSON Schema for url, extractMode, maxChars |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | string | URL to fetch |
| `extractMode` | string | Extraction mode: "markdown" or "text" |
| `maxChars` | integer | Maximum characters to extract |

#### Features
- SSRF protection
- Image detection and direct rendering
- Jina Reader API primary extractor
- Readability-lxml fallback
- HTML to Markdown conversion

---

## MCP Tools

**File:** `agent/tools/mcp.py`

### Helper Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `_extract_nullable_branch` | options | Any | Extract single non-null branch for nullable unions |
| `_normalize_schema_for_openai` | schema | dict | Normalize JSON Schema for OpenAI format |

---

### MCPToolWrapper

Wraps a single MCP server tool as a native nanobot Tool.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | Format: `mcp_{server_name}_{tool_name}` |

#### Features
- Timeout handling
- Error wrapping
- Converts MCP content blocks to text

---

### connect_mcp_servers

**File:** `agent/tools/mcp.py`

Async function to connect to MCP servers and register their tools.

```python
async def connect_mcp_servers(mcp_servers, registry, stack)
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mcp_servers` | list | List of MCP server configurations |
| `registry` | ToolRegistry | Tool registry to register tools |
| `stack` | AsyncExitStack | For cleanup management |

#### Transport Types
- stdio
- sse
- streamableHttp

#### Features
- Dynamic transport detection
- Tool filtering via `enabled_tools`
- Automatic schema normalization
- Per-tool timeout configuration

---

## Message Tool

**File:** `agent/tools/message.py`

### MessageTool

Send messages to users on chat channels.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"message"` |
| `description` | str | Send a message to a user |
| `parameters` | dict | JSON Schema for content, channel, chat_id, media |

#### Constructor

```python
def __init__(self, 
    send_callback: Callable | None = None, 
    default_channel: str = "",
    default_chat_id: str = "", 
    default_message_id: str | None = None)
```

#### Context Management

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `set_context` | channel, chat_id, message_id | None | Set current message context |
| `set_send_callback` | callback | None | Set message sending callback |
| `start_turn` | - | None | Reset per-turn send tracking |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `content` | string | Message content (required) |
| `channel` | string | Target channel (telegram, discord, etc.) |
| `chat_id` | string | Target chat/user ID |
| `media` | array | File paths to attach (images, audio, documents) |

---

## Cron Tool

**File:** `agent/tools/cron.py`

### CronTool

Schedule reminders and recurring tasks.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"cron"` |
| `description` | str | Schedule reminders and recurring tasks |
| `parameters` | dict | JSON Schema for action, message, every_seconds, cron_expr, tz, at, job_id |

#### Constructor

```python
def __init__(self, cron_service: CronService, default_timezone: str = "UTC")
```

#### Context Management

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `set_context` | channel, chat_id | None | Set delivery context |
| `set_cron_context` | active | None | Mark execution inside cron job |
| `reset_cron_context` | token | None | Restore previous context |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string (enum: add/list/remove) | Action to perform (required) |
| `message` | string | Reminder message (for add) |
| `every_seconds` | integer | Interval in seconds (recurring) |
| `cron_expr` | string | Cron expression (e.g., `0 9 * * *`) |
| `tz` | string | IANA timezone |
| `at` | string | ISO datetime for one-time execution |
| `job_id` | string | Job ID (for remove) |

#### Schedule Types
- `every_seconds` - Recurring interval
- `cron_expr` - Cron-based schedule
- `at` - One-time execution

---

## Spawn Tool

**File:** `agent/tools/spawn.py`

### SpawnTool

Spawn subagents for background task execution.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"spawn"` |
| `description` | str | Spawn a subagent to handle a task in the background |
| `parameters` | dict | JSON Schema for task, label |

#### Constructor

```python
def __init__(self, manager: "SubagentManager")
```

#### Context Management

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `set_context` | channel, chat_id | None | Set origin context for subagent announcements |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task` | string | Task for subagent (required) |
| `label` | string | Optional short label for display |

---

## Paperclip Tool

**File:** `agent/tools/paperclip.py`

### PaperclipTool

Interact with Paperclip task management system.

| Property/Method | Type | Description |
|-----------------|------|-------------|
| `name` | str | `"paperclip"` |
| `description` | str | Interact with Paperclip task management |
| `parameters` | dict | JSON Schema for action, status, priority, project_id, issue_id, etc. |

#### Constructor

```python
def __init__(self, 
    api_url: str = "http://127.0.0.1:3100", 
    company_id: str = "", 
    agent_id: str = "")
```

#### Actions

| Action | Description |
|--------|-------------|
| `list_tasks` | List tasks with optional filters |
| `get_task` | Get details of a specific task |
| `update_task` | Update task status/priority/description/title |
| `add_comment` | Add comment to a task |
| `create_task` | Create a new task |
| `fetch_my_tasks` | Get tasks assigned to this agent |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `action` | string | Action to perform (required) |
| `status` | string | Filter by status |
| `priority` | string | Filter by priority |
| `project_id` | string | Filter by project |
| `issue_id` | string | Task to operate on |
| `title` | string | Task title |
| `description` | string | Task description |
| `new_status` | string | Status for updates |
| `comment` | string | Comment text |

---

## Tool Definition Format (OpenAI)

```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "What the tool does",
        "parameters": { /* JSON Schema */ }
    }
}
```
