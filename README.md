<div align="center">
<img src="nanofoxy.png" alt="nanofoxy" width="500">
<h1>NanoFoxy: Ultra-Lightweight Personal AI Assistant</h1>
<p>
<a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
<a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
<img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
<img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>
</div>

🐈 **nanofoxy** is an **ultra-lightweight** personal AI assistant inspired by [OpenClaw](https://github.com/openclaw/openclaw).

⚡️ Delivers core agent functionality with **99% fewer lines of code** than OpenClaw.

> [!IMPORTANT]
> **Security note:** Due to `litellm` supply chain poisoning, **please check your Python environment ASAP**. We have fully removed `litellm` since **v0.1.4.post6**.

## Key Features

| Feature | Description |
|---------|-------------|
| **Ultra-Lightweight** | ~10K lines vs 1M+ in OpenClaw — faster, smaller, easier to understand |
| **Research-Ready** | Clean, readable code — easy to modify and extend |
| **Agent Loop** | LLM ↔ Tools execution with streaming responses |
| **Memory System** | Token-based persistent memory with QMD engine |
| **Skills** | Modular capability extensions (github, weather, cron, etc.) |
| **Dreaming** | Auto code review and self-improvement after REM phase |
| **Subagents** | Spawn background tasks and parallel agents |
| **MCP/ACP** | Model Context Protocol & Agent Client Protocol support |
| **Multi-Channel** | Telegram, Discord, WhatsApp, Feishu, Slack, Matrix, QQ, WeChat, Email, DingTalk, Wecom |
| **Multi-Provider** | OpenRouter, Anthropic, OpenAI, DeepSeek, Groq, Ollama, vLLM, Gemini, MiniMax, and more |

## Architecture

<p align="center">
<img src="nanobot_arch.png" alt="nanobot architecture" width="800">
</p>

## Install

```bash
# From source (recommended)
git clone https://github.com/HKUDS/nanobot.git
cd nanobot
pip install -e .

# Or from PyPI
pip install nanobot-ai
```

## Quick Start

```bash
# 1. Initialize
nanobot onboard

# 2. Configure (~/.nanobot/config.json)
# Set your API key and model:

{
  "providers": {
    "openrouter": {"apiKey": "sk-or-v1-xxx"}
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4-6",
      "provider": "openrouter"
    }
  }
}

# 3. Run
nanobot agent        # CLI chat
nanobot gateway      # Start with all enabled channels
```

## Chat Channels

| Channel | Setup |
|---------|-------|
| **Telegram** | Bot token from @BotFather |
| **Discord** | Bot token + Message Content intent |
| **WhatsApp** | `nanobot channels login whatsapp` |
| **WeChat** | `nanobot channels login weixin` |
| **Feishu** | App ID + App Secret |
| **Slack** | Bot token + App-Level token |
| **Matrix** | Homeserver URL + Access token |
| **Email** | IMAP/SMTP credentials |
| **QQ** | App ID + App Secret |
| **DingTalk** | App Key + App Secret |
| **Wecom** | Bot ID + Secret |
| **Mochat** | Auto-setup via nanobot |

### Telegram (Recommended)

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["YOUR_USER_ID"]
    }
  }
}
```

### TTS (Text-to-Speech)

Enable voice responses in Telegram using LFM2.5-Audio:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "tts_mode": "off"  // off, on, or auto
    }
  }
}
```

**TTS Modes:**
- `off` - Text only responses (default)
- `on` - Always speak responses via LFM2.5-Audio
- `auto` - Agent decides when to speak

**Commands:**
- `/tts on` - Enable voice responses
- `/tts off` - Disable voice responses  
- `/tts auto` - Let agent decide
- `/tts` - Show current TTS status

Note: TTS requires LFM2.5-Audio model files in `~/.nanobot/lfm2.5-audio-models/`

## Providers

| Provider | Description |
|----------|-------------|
| `openrouter` | Gateway to all models (recommended) |
| `anthropic` | Claude direct |
| `openai` | GPT direct |
| `deepseek` | DeepSeek direct |
| `groq` | LLM + Whisper transcription |
| `gemini` | Google Gemini |
| `ollama` | Local models |
| `vllm` | Local OpenAI-compatible |
| `azure_openai` | Enterprise Azure |
| `minimax` | Mainland China optimized |
| Custom | Any OpenAI-compatible API |

### Local Models (Ollama/vLLM)

```json
{
  "providers": {
    "ollama": {"apiBase": "http://localhost:11434"},
    "vllm": {"apiBase": "http://localhost:8000/v1"}
  },
  "agents": {
    "defaults": {
      "provider": "ollama",
      "model": "llama3.2"
    }
  }
}
```

## Configuration

### Web Search

```json
{
  "tools": {
    "web": {
      "search": {
        "provider": "brave",  // brave, tavily, jina, searxng, duckduckgo
        "apiKey": "YOUR_KEY"
      }
    }
  }
}
```

### MCP (Model Context Protocol)

```json
{
  "tools": {
    "mcpServers": {
      "filesystem": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
      }
    }
  }
}
```

### ACP (Agent Client Protocol)

```json
{
  "acp": {"enabled": true, "defaultAgent": "codex"},
  "channels": {"telegram": {"threadBindings": true}}
}
```

### Security

```json
{
  "tools": {
    "restrictToWorkspace": true,  // Sandbox all tools
    "exec": {"enable": true, "approvalMode": "supervised"}
  },
  "channels": {
    "telegram": {"allowFrom": ["*"]}  // Or specific IDs
  }
}
```

### Timezone

```json
{
  "agents": {"defaults": {"timezone": "Europe/Berlin"}}
}
```

### Memory & Dreaming

```json
{
  "tools": {
    "memory": {
      "dreaming": {
        "enabled": true,
        "autoCodeReview": true  // Auto-analyze logs and improve code
      }
    }
  }
}
```

## Skills

Built-in skills extend agent capabilities. List available skills with `/skills`.

| Skill | Description |
|-------|-------------|
| `github` | GitHub CLI operations (issues, PRs, CI) |
| `weather` | Weather via wttr.in / Open-Meteo |
| `cron` | Schedule reminders and tasks |
| `memory` | Two-layer memory system |
| `skill-creator` | Create new skills |
| `tmux` | Terminal session control |
| `summarize` | URL/file summarization |
| `obsidian` | Obsidian vault management |
| `notion` | Notion API operations |
| `slack` | Slack messaging |
| `himalaya` | Email via IMAP/SMTP |
| `code-reviewer` | Log analysis and code improvement |

### Add Custom Skills

Place skill folders in `{workspace}/skills/`:
```
workspace/skills/my-skill/SKILL.md
```

## Features

### Agent Features
- **LLM ↔ Tools Loop**: Core execution with tool calling
- **Streaming**: End-to-end token streaming
- **Subagents**: Spawn background tasks
- **Memory**: Token-based with QMD engine
- **Skills**: Loadable capability modules
- **Cron**: One-shot and recurring schedules
- **Heartbeat**: Periodic wake-up tasks
- **MCP/ACP**: External tool and agent protocols

### Memory System
- **Short-term**: Session history with token tracking
- **Long-term**: MEMORY.md + HISTORY.md
- **Dreaming**: Auto-consolidation phases (Light, Deep, REM)
- **Auto Code Review**: Analyzes logs after REM, improves code, restarts service

### Security
- **Workspace Restriction**: Sandbox all file/shell tools
- **Access Control**: Whitelist-based allowFrom
- **Exec Approvals**: Supervised or yolo mode

## CLI Reference

| Command | Description |
|---------|-------------|
| `nanobot onboard` | Initialize config & workspace |
| `nanobot agent -m "..."` | Chat with agent |
| `nanobot gateway` | Start gateway (all channels) |
| `nanobot gateway -p <port>` | Custom port |
| `nanobot status` | Show status |
| `nanobot channels login whatsapp` | QR login for WhatsApp |
| `nanobot memory --status` | Show memory/dreaming status |
| `nanobot memory --dreaming light` | Run dreaming phase |

### Options
- `-c, --config <path>` — Config file
- `-w, --workspace <path>` — Workspace directory
- `-p, --port <port>` — Gateway port (default: 18790)
- `--no-markdown` — Plain text output
- `--logs` — Show runtime logs

## Docker

```bash
# Build
docker build -t nanobot .

# Run gateway
docker run -v ~/.nanobot:/root/.nanobot -p 18790:18790 nanobot

# CLI
docker run -v ~/.nanobot:/root/.nanobot --rm nanobot agent -m "Hello"
```

## Multiple Instances

```bash
# Different configs/workspaces
nanobot onboard --config ~/.nanobot-telegram/config.json --workspace ~/.nanobot-telegram/workspace
nanobot onboard --config ~/.nanobot-discord/config.json --workspace ~/.nanobot-discord/workspace

# Run separate instances
nanobot gateway --config ~/.nanobot-telegram/config.json
nanobot gateway --config ~/.nanobot-discord/config.json -p 18791
```

## Project Structure

```
nanobot/
├── agent/           # Core agent logic
│   ├── loop.py      # LLM ↔ tools execution
│   ├── context.py   # Prompt builder
│   ├── memory/      # Memory & dreaming
│   ├── skills.py    # Skills loader
│   └── tools/       # Built-in tools
├── skills/          # Bundled skills
├── channels/        # Chat integrations
├── providers/       # LLM providers
├── bus/             # Message routing
├── cron/            # Scheduled tasks
├── session/         # Conversation sessions
├── config/          # Configuration
└── cli/             # Commands
```

## Contributing

PRs welcome! The codebase is intentionally small and readable.

- `main` — Stable releases
- `nightly` — Experimental features

---

<p align="center">
<em>Thanks for using nanobot!</em>
</p>