# Agent

The agent module is the core of nanobot's autonomous operation. It handles the agent loop, context building, memory management, skill loading, and tool execution orchestration.

## Files

| File | Description |
|------|-------------|
| `agent/__init__.py` | Package initialization |
| `agent/loop.py` | Main agent loop implementation |
| `agent/context.py` | Context builder for agent prompts |
| `agent/hook.py` | Lifecycle hooks for agent runs |
| `agent/memory.py` | Two-layer memory system |
| `agent/runner.py` | Shared execution loop for tool-using agents |
| `agent/skills.py` | Skills loader for agent capabilities |
| `agent/subagent.py` | Re-exports AgentLoop |

---

## Classes

### AgentLoop

**File:** `agent/loop.py`

The main orchestrator class that processes messages, manages sessions, and coordinates with memory consolidation.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | message_bus, tools, model, sessions, memory_consolidator, commands, context_builder, provider, config, channel_manager | - | Initialize the agent loop with all dependencies |
| `_connect_mcp` | - | None | Connect to MCP (Model Context Protocol) servers |
| `_set_tool_context` | channel, chat_id, message_id | None | Set context for tool execution (message tool, cron tool, etc.) |
| `_strip_think` | text | str | Remove think blocks that models embed in content |
| `_tool_hint` | tool_calls | str | Format tool calls as concise hint |
| `_run_agent_loop` | messages, hook, max_iterations, ... | AgentRunResult | Run the agent iteration loop using AgentRunner |
| `run` | - | None | Main run loop - consumes inbound messages and dispatches to _dispatch |
| `_dispatch` | msg | None | Process a message: per-session serial, cross-session concurrent |
| `close_mcp` | - | None | Drain pending background archives, then close MCP connections |
| `_schedule_background` | coro | Task | Schedule a coroutine as a tracked background task |
| `stop` | - | None | Stop the agent loop |
| `_process_message` | inbound | OutboundPayload | Process a single inbound message and return response |
| `_image_placeholder` | block | str | Convert inline image block to text placeholder |
| `_sanitize_persisted_blocks` | blocks | list | Strip volatile multimodal payloads before writing session history |
| `_save_turn` | session, user_msg, assistant_msg, tool_results | None | Save new-turn messages into session, truncating large tool results |
| `process_direct` | text, media | OutboundPayload | Process a message directly and return outbound payload |

---

### ContextBuilder

**File:** `agent/context.py`

Builds the context (system prompt + messages) for the agent.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace, timezone | - | Initialize with workspace path and timezone |
| `build_system_prompt` | skill_names | str | Build system prompt from identity, bootstrap files, memory, and skills |
| `_get_identity` | - | str | Returns the core identity section with platform info, workspace path, and guidelines |
| `_build_runtime_context` | channel, chat_id, timezone | str | Build untrusted runtime metadata block for injection before user message |
| `_load_bootstrap_files` | - | list[str] | Load bootstrap files (AGENTS.md, SOUL.md, USER.md, TOOLS.md) |
| `build_messages` | channel, chat_id, timezone, session, message, media | list[dict] | Build complete message list for an LLM call |
| `_build_user_content` | text, media | list | Build user message content with optional base64-encoded images |
| `add_tool_result` | messages, tool_call_id, content | None | Add a tool result to the message list |
| `add_assistant_message` | messages, content, tool_calls | None | Add an assistant message to the message list |

---

### AgentHookContext

**File:** `agent/hook.py`

A dataclass representing mutable per-iteration state exposed to runner hooks.

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | int | Current iteration number |
| `messages` | list[dict] | Message history |
| `response` | LLMResponse | LLM response (optional) |
| `usage` | dict | Token usage |
| `tool_calls` | list[ToolCallRequest] | Tool calls to execute |
| `tool_results` | list | Results from tool execution |
| `tool_events` | list[dict] | Tool execution events |
| `final_content` | str | Final response content |
| `stop_reason` | str | Why the loop stopped |
| `error` | str | Error message if any |

---

### AgentHook

**File:** `agent/hook.py`

Minimal lifecycle surface for shared runner customization.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `wants_streaming` | - | bool | Returns True if streaming is desired (default: False) |
| `before_iteration` | context | None | Hook called before each iteration |
| `on_stream` | context, delta | None | Hook called with each content delta during streaming |
| `on_stream_end` | context, resuming | None | Hook called when streaming session finishes |
| `before_execute_tools` | context | None | Hook called before executing tool calls |
| `after_iteration` | context | None | Hook called after each iteration |
| `finalize_content` | context, content | str | Finalize/content cleanup before returning |

---

### MemoryStore

**File:** `agent/memory.py`

Two-layer memory system - MEMORY.md (long-term facts) + HISTORY.md (grep-searchable log).

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace | - | Initialize with workspace path |
| `read_long_term` | - | str | Read MEMORY.md content |
| `_create_backup` | - | None | Create timestamped backup of MEMORY.md before writing |
| `_cleanup_old_backups` | - | None | Remove old backups beyond limit |
| `write_long_term` | content | None | Write long-term memory with automatic backup |
| `update_memory_safely` | new_memory | None | Update memory with backup and validation |
| `_validate_memory_update` | old, new | bool | Validate that memory update doesn't lose important content |
| `merge_memory_update` | update | None | Merge new memory with existing (appends under dated section) |
| `append_history` | entry | None | Append entry to HISTORY.md |
| `get_memory_context` | - | str | Get long-term memory for context injection |
| `get_memory_summary` | max_facts | str | Get summary of memory facts |
| `search_memory` | query | str | Search memory and history for query string |
| `_format_messages` | messages | str | Format messages for consolidation prompt |
| `consolidate` | messages, provider, model, context_settings | None | Consolidate messages into MEMORY.md + HISTORY.md using LLM |
| `_fail_or_raw_archive` | messages | None | Increment failure count; after threshold, raw-archive messages |
| `_raw_archive` | messages | None | Fallback: dump raw messages to HISTORY.md |

---

### MemoryConsolidator

**File:** `agent/memory.py`

Owns consolidation policy, locking, and session offset updates.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace, provider, model, sessions, context_settings | - | Initialize with all dependencies |
| `get_lock` | session_key | Lock | Return the shared consolidation lock for one session |
| `consolidate_messages` | messages | None | Archive selected message chunk into persistent memory |
| `pick_consolidation_boundary` | session, tokens_to_remove | int | Pick user-turn boundary that removes enough old prompt tokens |
| `estimate_session_prompt_tokens` | session | int | Estimate current prompt size for session history view |
| `archive_messages` | messages | None | Archive messages with guaranteed persistence |
| `maybe_consolidate_by_tokens` | session | None | Loop: archive old messages until prompt fits within safe budget |

---

### AgentRunSpec

**File:** `agent/runner.py`

A dataclass containing configuration for a single agent execution.

| Field | Type | Description |
|-------|------|-------------|
| `initial_messages` | list[dict] | Initial message list |
| `tools` | ToolRegistry | Tool registry |
| `model` | str | Model name |
| `max_iterations` | int | Max tool call iterations |
| `temperature` | float | Temperature setting (optional) |
| `max_tokens` | int | Max tokens (optional) |
| `reasoning_effort` | str | Reasoning effort (optional) |
| `hook` | AgentHook | Lifecycle hook |
| `error_message` | str | Error message |
| `max_iterations_message` | str | Max iterations message |
| `concurrent_tools` | bool | Run tools concurrently |
| `fail_on_tool_error` | bool | Fail on tool error |

---

### AgentRunResult

**File:** `agent/runner.py`

A dataclass representing the outcome of a shared agent execution.

| Field | Type | Description |
|-------|------|-------------|
| `final_content` | str | Final response |
| `messages` | list[dict] | All messages |
| `tools_used` | list[str] | Tools used |
| `usage` | dict | Token usage |
| `stop_reason` | str | Why loop stopped |
| `error` | str | Error message |
| `tool_events` | list[dict] | Tool events |

---

### AgentRunner

**File:** `agent/runner.py`

Run a tool-capable LLM loop without product-layer concerns.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | provider | - | Initialize with LLM provider |
| `run` | spec | AgentRunResult | Execute the agent loop with given spec |
| `_execute_tools` | spec, tool_calls | list | Execute multiple tool calls (concurrent or sequential) |
| `_run_tool` | spec, tool_call | dict | Run a single tool and return result with event |

---

### SkillsLoader

**File:** `agent/skills.py`

Loader for agent skills (markdown files that teach the agent capabilities).

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | workspace, builtin_skills_dir | - | Initialize with workspace and optional builtin skills directory |
| `list_skills` | filter_unavailable | list[dict] | List all available skills with optional filtering |
| `load_skill` | name | str | Load a skill by name |
| `load_skills_for_context` | skill_names | dict[str, str] | Load specific skills for inclusion in agent context |
| `build_skills_summary` | - | str | Build XML-formatted summary of all skills |
| `_get_missing_requirements` | skill_meta | str | Get description of missing requirements |
| `_get_skill_description` | name | str | Get skill description from frontmatter |
| `_strip_frontmatter` | content | str | Remove YAML frontmatter from markdown |
| `_parse_nanobot_metadata` | raw | dict | Parse skill metadata JSON from frontmatter |
| `_check_requirements` | skill_meta | tuple[bool, str] | Check if skill requirements are met |
| `_get_skill_meta` | name | dict | Get nanobot metadata for a skill |
| `get_always_skills` | - | list[str] | Get skills marked as always=true |
| `get_skill_metadata` | name | dict | Get metadata from skill's frontmatter |

---

### subagent.py

**File:** `agent/subagent.py`

Simply re-exports the `AgentLoop` class from `loop.py` for backwards compatibility or alternative import path.

```python
from nanobot.agent.loop import AgentLoop

__all__ = ["AgentLoop"]
```

---

## Data Flow

```
                    ┌─────────────────────────────────────────────────────┐
                    │                    AgentLoop                       │
                    │                 (loop.py - main orchestrator)      │
                    └──────────────────────┬──────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────────────┐
                    │                      │                              │
                    ▼                      ▼                              ▼
          ┌─────────────────┐    ┌──────────────────┐      ┌────────────────────┐
          │   ContextBuilder│    │ MemoryConsolidator│      │    ToolRegistry    │
          │   (context.py)  │    │    (memory.py)    │      │   (agent/tools/)    │
          └────────┬────────┘    └─────────┬─────────┘      └────────────────────┘
                   │                        │
                   │                        │
          ┌────────┴────────┐    ┌────────┴────────┐
          │   SkillsLoader    │    │   MemoryStore    │
          │   (skills.py)    │    │   (memory.py)     │
          └───────────────────┘    └───────────────────┘
                                         
                    ┌──────────────────────────────────────┐
                    │           AgentRunner                │
                    │          (runner.py)                  │
                    │                                      │
                    │  Uses:                               │
                    │  - LLMProvider (providers/)          │
                    │  - ToolRegistry (agent/tools/)       │
                    │  - AgentHook (hook.py)               │
                    │  - AgentHookContext (hook.py)        │
                    └──────────────────────────────────────┘
```

1. **AgentLoop.run()** continuously consumes inbound messages from the message bus
2. For each message, it uses **ContextBuilder** to build messages (system prompt + history + current message)
3. **ContextBuilder** incorporates:
   - Identity/guidelines from `_get_identity()`
   - Bootstrap files (AGENTS.md, SOUL.md, USER.md, TOOLS.md)
   - Long-term memory from **MemoryStore**
   - Skills from **SkillsLoader**
4. **AgentLoop._run_agent_loop()** delegates to **AgentRunner**
5. **AgentRunner** executes the LLM loop:
   - Calls LLM via provider
   - Executes tools via ToolRegistry
   - Uses **AgentHook** for lifecycle events (streaming, progress, etc.)
6. **MemoryConsolidator** manages memory:
   - Estimates token usage
   - Calls **MemoryStore** to consolidate old messages into MEMORY.md/HISTORY.md
7. **SkillsLoader** provides skill content for the system prompt
