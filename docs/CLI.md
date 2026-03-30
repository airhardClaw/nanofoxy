# CLI

The CLI module provides the command-line interface for nanobot. It includes commands, models for data structures, onboarding, and streaming support.

## Files

| File | Description |
|------|-------------|
| `cli/__init__.py` | Module initialization |
| `cli/commands.py` | CLI command definitions |
| `cli/models.py` | Pydantic models for CLI data |
| `cli/onboard.py` | Onboarding flow |
| `cli/stream.py` | Streaming utilities |

---

## Commands

**File:** `cli/commands.py`

### CLI Commands

| Command | Description |
|---------|-------------|
| `interactive` | Start nanobot in interactive mode |
| `run` | Run nanobot with specified configuration |
| `config` | Manage configuration |
| `skills` | List available skills |
| `serve` | Start the web dashboard |

### Key Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `interactive` | - | None | Start interactive chat session |
| `run` | config_path | None | Run nanobot with config file |
| `main` | - | None | Main entry point for CLI |

---

## Models

**File:** `cli/models.py`

### CLI Models

| Model | Description |
|-------|-------------|
| `Message` | Represents a chat message |
| `ConfigShow` | Configuration display model |
| `SkillInfo` | Skill information model |

---

## Onboarding

**File:** `cli/onboard.py`

### Onboarding Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `check_workspace` | workspace | None | Check and create workspace if needed |
| `setup_config` | workspace | None | Guide user through initial configuration |
| `select_provider` | - | str | Interactively select LLM provider |
| `select_channels` | - | list[str] | Interactively select messaging channels |

### Onboarding Steps
1. Create workspace directory
2. Set up initial configuration file
3. Select LLM provider and configure API keys
4. Select messaging channels
5. Test configuration

---

## Streaming

**File:** `cli/stream.py`

### Streaming Utilities

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `StreamPrinter` | - | - | Class for printing streaming responses |
| `print_stream` | response, delay | None | Print response with typewriter effect |
| `create_stream_callback` | printer | callback | Create callback for streaming |

### StreamPrinter Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `__init__` | delay | - | Initialize with character delay |
| `print` | text | None | Print text with delay |
| `flush` | - | None | Flush output |

---

## Usage

### Interactive Mode
```bash
nanobot interactive
```

### Run with Config
```bash
nanobot run --config config.yaml
```

### Web Dashboard
```bash
nanobot serve --host 0.0.0.0 --port 18791
```
