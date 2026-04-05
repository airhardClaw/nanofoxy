# Config

The config module handles configuration loading, schema validation, and path management for nanobot.

## Files

| File | Description |
|------|-------------|
| `config/__init__.py` | Module initialization |
| `config/loader.py` | Configuration loading from YAML |
| `config/schema.py` | Configuration schema definitions |
| `config/paths.py` | Path management utilities |

---

## Loader

**File:** `config/loader.py`

### ConfigLoader

Loads and validates configuration from YAML files.

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | config_path | - | Initialize with config file path |
| `load` | - | Config | Load and validate configuration |
| `load_from_dict` | data | Config | Load from dictionary |
| `_validate` | config | None | Validate configuration |
| `_resolve_env_vars` | config | None | Resolve environment variables |

---

## Schema

**File:** `config/schema.py`

### Config

Main configuration model.

| Field | Type | Description |
|-------|------|-------------|
| `provider` | dict | LLM provider configuration |
| `model` | str | Model name |
| `workspace` | Path | Workspace directory |
| `channels` | dict | Channel configurations |
| `commands` | dict | Command configurations |
| `mcp` | dict | MCP server configurations |
| `memory` | dict | Memory settings |
| `session` | dict | Session settings |

### ProviderConfig

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Provider name (openai, anthropic, etc.) |
| `api_key` | str | API key |
| `api_base` | str | API base URL |
| `model` | str | Model name |

### ChannelConfig

| Field | Type | Description |
|-------|------|-------------|
| `enabled` | bool | Whether channel is enabled |
| `config` | dict | Channel-specific configuration |

---

## Paths

**File:** `config/paths.py`

### Path Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `get_workspace_path` | config | Path | Get workspace path from config |
| `get_data_path` | workspace | Path | Get data directory path |
| `get_cache_path` | workspace | Path | Get cache directory path |
| `get_config_path` | - | Path | Get default config file path |
| `ensure_workspace` | workspace | None | Create workspace directories |

---

## LM Studio Configuration (Qwen2.5-8B)

Example for running Qwen2.5-8B (Q4_K_S) via LM Studio:

```yaml
# LM Studio with Qwen2.5-8B (Q4_K_S)
provider:
  name: lmstudio
  api_base: http://localhost:1234/v1
  # No api_key needed for local

agents:
  defaults:
    model: qwen2.5-8b-instruct
    contextWindowTokens: 128000
    maxTokens: 4096
    temperature: 0.7
    maxToolIterations: 30

channels:
  telegram:
    enabled: true
    config:
      token: ${TELEGRAM_BOT_TOKEN}
      streaming: true  # Enable streaming for faster responses
```

**Requirements:**
- LM Studio running with Qwen2.5-8B model loaded
- API server enabled on port 1234 (default)

---

## Configuration File Example

```yaml
provider:
  name: openai
  api_key: ${OPENAI_API_KEY}
  model: gpt-4o

workspace: ./workspace

channels:
  telegram:
    enabled: true
    config:
      token: ${TELEGRAM_BOT_TOKEN}
  discord:
    enabled: true
      token: ${DISCORD_BOT_TOKEN}

memory:
  consolidate_tokens: 6000
  snapshot_interval: 100

session:
  max_history: 50
  ttl: 86400
```
