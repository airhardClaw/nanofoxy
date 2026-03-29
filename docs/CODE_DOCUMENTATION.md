# Nanobot Code Documentation

## Overview

Nanobot is an ultra-lightweight personal AI assistant (~99% fewer lines than OpenClaw). It provides core agent functionality with minimal footprint, making it fast, easy to understand, and extendable.

**Version:** 0.1.4.post6

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Channels                                │
│  (Telegram, Slack, Discord, Feishu, WeChat, QQ, etc.)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        Message Bus                           │
│                    (Event Queue System)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Agent Loop                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │
│  │   Context    │  │    Memory    │  │  Tool Registry  │   │
│  │   Builder    │  │    Store     │  │                 │   │
│  └─────────────┘  └─────────────┘  └─────────────────┘   │
│                              │                              │
│                     ┌──────────────┐                       │
│                     │   LLM Loop   │                       │
│                     │  (Runner)    │                       │
│                     └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Providers                              │
│     (OpenAI, Anthropic, DeepSeek, Ollama, etc.)            │
└─────────────────────────────────────────────────────────────┘
```

## Module Structure

### `nanobot/`

Core package containing all agent functionality.

#### `nanobot/agent/`

Core agent implementation.

| File | Description |
|------|-------------|
| `loop.py` | **AgentLoop** - Core processing engine. Receives messages, builds context, calls LLM, executes tools, sends responses |
| `context.py` | **ContextBuilder** - Builds conversation context with history and memory |
| `memory.py` | **MemoryStore** - Token-based memory system for storing and retrieving conversation history |
| `runner.py` | **AgentRunner** - Executes LLM calls and handles responses |
| `subagent.py` | **SubagentManager** - Manages sub-agent spawning and lifecycle |
| `skills.py` | **SkillsLoader** - Loads and manages agent skills |
| `hook.py` | **AgentHook** - Lifecycle hooks for agent events |

#### `nanobot/agent/tools/`

Built-in tools available to the agent.

| File | Description |
|------|-------------|
| `filesystem.py` | File operations: ReadFileTool, WriteFileTool, EditFileTool, ListDirTool |
| `shell.py` | **ExecTool** - Execute shell commands |
| `message.py` | **MessageTool** - Send messages to channels |
| `web.py` | Web tools: WebFetchTool, WebSearchTool |
| `cron.py` | **CronTool** - Schedule and manage tasks |
| `spawn.py` | **SpawnTool** - Spawn sub-agents |
| `registry.py` | **ToolRegistry** - Central tool registration and discovery |

#### `nanobot/bus/`

Message bus system for event handling.

| File | Description |
|------|-------------|
| `events.py` | Event types: InboundMessage, OutboundMessage |
| `queue.py` | **MessageBus** - Async message queue system |

#### `nanobot/channels/`

Communication channel integrations.

| File | Description |
|------|-------------|
| `telegram.py` | Telegram bot integration |
| `slack.py` | Slack integration |
| `discord.py` | Discord bot integration |
| `feishu.py` | Feishu (Lark) integration |
| `wechat.py` | WeChat integration |
| `qq.py` | QQ/Tencent IM integration |
| `matrix.py` | Matrix protocol integration |
| `whatsapp.py` | WhatsApp integration |
| `wecom.py` | WeCom integration |
| `dingtalk.py` | DingTalk integration |
| `email.py` | Email integration |
| `web.py` | Web UI interface |

#### `nanobot/command/`

Command routing and built-in commands.

| File | Description |
|------|-------------|
| `router.py` | **CommandRouter** - Routes commands to handlers |
| `builtin.py` | Built-in commands (/help, /status, /restart, etc.) |

#### `nanobot/providers/`

LLM provider implementations.

| File | Description |
|------|-------------|
| `base.py` | **LLMProvider** - Base provider interface |
| `openai.py` | OpenAI API |
| `anthropic.py` | Anthropic Claude API |
| `deepseek.py` | DeepSeek API |
| `ollama.py` | Ollama local models |
| `azure.py` | Azure OpenAI |
| `volcengine.py` | VolcEngine (ByteDance) |
| `stepfun.py` | StepFun |

#### `nanobot/session/`

User session management.

| File | Description |
|------|-------------|
| `manager.py` | **SessionManager** - Manages user sessions and history |

#### `nanobot/cron/`

Scheduled task functionality.

| File | Description |
|------|-------------|
| `service.py` | **CronService** - Schedules and executes periodic tasks |

#### `nanobot/config/`

Configuration management.

| File | Description |
|------|-------------|
| `schema.py` | Configuration data classes |
| `loader.py` | Config file loading |

#### `nanobot/security/`

Security features.

| File | Description |
|------|-------------|
| `access.py` | Access control and permissions |

#### `nanobot/cli/`

Command-line interface.

| File | Description |
|------|-------------|
| `main.py` | CLI entry point |
| `setup.py` | Interactive setup wizard |

## Core Concepts

### Agent Loop Flow

1. **Receive Message** - Message arrives via channel
2. **Build Context** - ContextBuilder creates context with history and memory
3. **LLM Call** - AgentRunner calls the LLM with context
4. **Tool Execution** - If LLM returns tool calls, execute them
5. **Response** - Send response back via message bus

### Memory System

Nanobot uses a token-based memory system that:
- Consolidates conversation history periodically
- Stores memories in the workspace
- Supports context window optimization

### Tool System

Tools are registered in the ToolRegistry and can be:
- **Built-in**: Filesystem, shell, message, web, cron, spawn
- **MCP**: Model Context Protocol tools
- **Custom**: User-defined skills

### Channel Integration

Channels receive messages and publish to the message bus. The agent processes messages and publishes responses back to the bus, which channels then deliver to users.

## Usage

### Running Nanobot

```bash
# Interactive setup
nanobot setup

# Run with config
nanobot run

# Via Docker
docker run -v ~/.nanobot:/root/.nanobot hkuds/nanobot
```

### Configuration

Config file location: `~/.nanobot/config.yaml`

```yaml
provider:
  type: openai
  api_key: ${OPENAI_API_KEY}

channels:
  telegram:
    bot_token: ${TELEGRAM_BOT_TOKEN}
```

## Development

### Adding a New Channel

1. Create `nanobot/channels/<channel_name>.py`
2. Implement channel interface (login, receive, send)
3. Register in `nanobot/channels/__init__.py`

### Adding a New Provider

1. Create `nanobot/providers/<provider_name>.py`
2. Extend `LLMProvider` base class
3. Implement chat completion method

### Creating Custom Skills

Skills go in `~/.nanobot/skills/` directory.

```
~/.nanobot/skills/
  my_skill/
    prompt.md      # Skill definition
    tools.yaml     # Optional tool definitions
```
