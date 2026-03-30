# CLI User Guide

This guide covers all command-line interface (CLI) commands available in nanobot.

## Table of Contents

- [Global Options](#global-options)
- [Main Commands](#main-commands)
  - [nanobot](#nanobot)
  - [nanobot agent](#nanobot-agent)
  - [nanobot gateway](#nanobot-gateway)
  - [nanobot web](#nanobot-web)
  - [nanobot onboard](#nanobot-onboard)
  - [nanobot status](#nanobot-status)
- [Channel Commands](#channel-commands)
  - [nanobot channels status](#nanobot-channels-status)
  - [nanobot channels login](#nanobot-channels-login)
- [Plugin Commands](#plugin-commands)
  - [nanobot plugins list](#nanobot-plugins-list)
- [Paperclip Commands](#paperclip-commands)
  - [nanobot paperclip list](#nanobot-paperclip-list)
  - [nanobot paperclip fetch](#nanobot-paperclip-fetch)
  - [nanobot paperclip show](#nanobot-paperclip-show)
  - [nanobot paperclip complete](#nanobot-paperclip-complete)
  - [nanobot paperclip update](#nanobot-paperclip-update)
  - [nanobot paperclip comment](#nanobot-paperclip-comment)
- [Provider Commands](#provider-commands)
  - [nanobot provider login](#nanobot-provider-login)
- [In-Chat Commands](#in-chat-commands)
  - [/new](#new)
  - [/stop](#stop)
  - [/restart](#restart)
  - [/status](#status)
  - [/skills](#skills)
  - [/help](#help)
  - [$skill-name](#skill-name)

---

## Global Options

| Option | Description |
|--------|-------------|
| `--version, -v` | Show version number |
| `--help, -h` | Show help message |

---

## Main Commands

### nanobot

```
nanobot [--version] [--help]
```

Main entry point for the nanobot CLI.

**Options:**
- `--version, -v` - Show version and exit
- `--help, -h` - Show help message

---

### nanobot agent

```
nanobot agent [OPTIONS]
```

Interact with the agent directly. Can be used in single-message mode or interactive mode.

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--message TEXT` | `-m` | Message to send to the agent (if not provided, starts interactive mode) |
| `--session TEXT` | `-s` | Session ID (default: `cli:direct`) |
| `--workspace PATH` | `-w` | Workspace directory |
| `--config PATH` | `-c` | Config file path |
| `--markdown / --no-markdown` | | Render assistant output as Markdown (default: True) |
| `--logs / --no-logs` | | Show nanobot runtime logs during chat (default: False) |

**Examples:**

```bash
# Send a single message
nanobot agent -m "Hello, how are you?"

# Interactive chat mode
nanobot agent

# With custom config
nanobot agent -c /path/to/config.yaml -m "What's the weather?"

# With custom session
nanobot agent -s "telegram:123456" -m "Hello"
```

---

### nanobot gateway

```
nanobot gateway [OPTIONS]
```

Start the nanobot gateway - the main server mode that handles incoming messages from all configured channels.

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--port INTEGER` | `-p` | Gateway port |
| `--workspace PATH` | `-w` | Workspace directory |
| `--verbose` | `-v` | Verbose output (debug logging) |
| `--config PATH` | `-c` | Path to config file |
| `--web` | | Enable web dashboard (runs on port 18791) |
| `--web-port INTEGER` | | Web dashboard port (default: 18791) |
| `--paperclip-poll` | | Enable Paperclip task polling |

**Examples:**

```bash
# Start gateway with all defaults
nanobot gateway

# Start with web dashboard
nanobot gateway --web

# Start with custom port
nanobot gateway -p 8080

# Verbose mode for debugging
nanobot gateway --verbose

# With Paperclip polling
nanobot gateway --paperclip-poll
```

---

### nanobot web

```
nanobot web [OPTIONS]
```

Start the NanoFoxy web dashboard (API only, no agent loop).

**Options:**

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--port INTEGER` | `-p` | 18791 | Web dashboard port |
| `--host TEXT` | `-h` | 127.0.0.1 | Web dashboard host |
| `--workspace PATH` | `-w` | | Workspace directory |
| `--config PATH` | `-c` | | Path to config file |

**Examples:**

```bash
# Start web dashboard on default port
nanobot web

# Start on custom port
nanobot web -p 8080

# Start on custom host
nanobot web -h 0.0.0.0 -p 3000
```

---

### nanobot onboard

```
nanobot onboard [OPTIONS]
```

Initialize nanobot configuration and workspace.

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--workspace PATH` | `-w` | Workspace directory |
| `--config PATH` | `-c` | Path to config file |
| `--wizard` | | Use interactive wizard for configuration |

**Examples:**

```bash
# Create default configuration
nanobot onboard

# With custom workspace
nanobot onboard -w /path/to/workspace

# Use interactive wizard
nanobot onboard --wizard
```

---

### nanobot status

```
nanobot status
```

Show nanobot status including:
- Config file location and existence
- Workspace location and existence
- Current model
- API keys configured for each provider

**Examples:**

```bash
nanobot status
```

---

## Channel Commands

### nanobot channels status

```
nanobot channels status
```

Show status of all available channels (built-in and plugins).

**Examples:**

```bash
nanobot channels status
```

Output example:
```
┌──────────┬─────────┐
│ Channel  │ Enabled │
├──────────┼─────────┤
│ Discord  │    ✓    │
│ Telegram │    ✓    │
│ Slack    │    ✗    │
└──────────┴─────────┘
```

---

### nanobot channels login

```
nanobot channels login CHANNEL_NAME [OPTIONS]
```

Authenticate with a channel via QR code or other interactive login.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `CHANNEL_NAME` | Channel name (e.g., weixin, whatsapp) |

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--force` | `-f` | Force re-authentication even if already logged in |

**Examples:**

```bash
# Login to WeChat
nanobot channels login weixin

# Login to WhatsApp (force re-auth)
nanobot channels login whatsapp --force
```

---

## Plugin Commands

### nanobot plugins list

```
nanobot plugins list
```

List all discovered channels (built-in and plugins) with their source and enabled status.

**Examples:**

```bash
nanobot plugins list
```

---

## Paperclip Commands

### nanobot paperclip list

```
nanobot paperclip list [OPTIONS]
```

List tasks from Paperclip.

**Options:**

| Option | Alias | Default | Description |
|--------|-------|---------|-------------|
| `--status TEXT` | `-s` | | Filter by status |
| `--priority TEXT` | `-p` | | Filter by priority |
| `--limit INTEGER` | `-l` | 50 | Max results |

**Examples:**

```bash
# List all tasks
nanobot paperclip list

# Filter by status
nanobot paperclip list --status in_progress

# Filter by priority
nanobot paperclip list --priority high
```

---

### nanobot paperclip fetch

```
nanobot paperclip fetch
```

Fetch tasks assigned to this agent.

**Examples:**

```bash
nanobot paperclip fetch
```

---

### nanobot paperclip show

```
nanobot paperclip show ISSUE_ID
```

Show details of a specific task.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `ISSUE_ID` | Issue ID to display |

**Examples:**

```bash
nanobot paperclip show TASK-123
```

---

### nanobot paperclip complete

```
nanobot paperclip complete ISSUE_ID [OPTIONS]
```

Mark a task as completed.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `ISSUE_ID` | Issue ID to complete |

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--comment TEXT` | `-c` | Completion comment |

**Examples:**

```bash
# Complete a task
nanobot paperclip complete TASK-123

# With completion comment
nanobot paperclip complete TASK-123 -c "Done!"
```

---

### nanobot paperclip update

```
nanobot paperclip update ISSUE_ID [OPTIONS]
```

Update task status or priority.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `ISSUE_ID` | Issue ID to update |

**Options:**

| Option | Alias | Description |
|--------|-------|-------------|
| `--status TEXT` | `-s` | New status |
| `--priority TEXT` | `-p` | New priority |

**Examples:**

```bash
# Update status
nanobot paperclip update TASK-123 --status done

# Update priority
nanobot paperclip update TASK-123 --priority high

# Update both
nanobot paperclip update TASK-123 -s in_progress -p urgent
```

---

### nanobot paperclip comment

```
nanobot paperclip comment ISSUE_ID BODY
```

Add a comment to a task.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `ISSUE_ID` | Issue ID |
| `BODY` | Comment text |

**Examples:**

```bash
nanobot paperclip comment TASK-123 "Working on this now"
```

---

## Provider Commands

### nanobot provider login

```
nanobot provider login PROVIDER
```

Authenticate with an OAuth provider.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `PROVIDER` | OAuth provider name (e.g., 'openai-codex', 'github-copilot') |

**Examples:**

```bash
# Login to OpenAI Codex
nanobot provider login openai-codex

# Login to GitHub Copilot
nanobot provider login github-copilot
```

---

## In-Chat Commands

These commands can be used while chatting with the agent in any channel (CLI, Telegram, Discord, etc.).

### /new

```
/new
```

Start a fresh conversation. Clears the current session history but archives previous messages to memory.

**Example:**
```
You: /new
nanobot: New session started.
```

---

### /stop

```
/stop
```

Cancel all active tasks and subagents for the current session.

**Example:**
```
You: /stop
nanobot: Stopped 2 task(s).
```

---

### /restart

```
/restart
```

Restart the bot process in-place. Useful for applying configuration changes.

**Example:**
```
You: /restart
nanobot: Restarting...
```

---

### /status

```
/status
```

Show bot status including:
- Version
- Current model
- Uptime
- Token usage
- Session message count

**Example:**
```
You: /status
nanobot: 🦊 nanobot v2.0.0 | gpt-4o | Uptime: 5m 32s | Tokens: 1,234 prompt / 567 completion
```

---

### /skills

```
/skills
```

List all available skills. Skills are capabilities the agent can use.

**Example:**
```
You: /skills
nanobot: Available skills (use $<name> to activate):
  ✓ weather — Get weather information
  ✓ memory — Query agent memory
  ✓ cron — Schedule reminders
  ✗ github — GitHub integration (missing: github_token)
```

---

### /help

```
/help
```

Show available commands.

**Example:**
```
You: /help
nanobot: 🐈 nanobot commands:
  /new — Start a new conversation
  /stop — Stop the current task
  /restart — Restart the bot
  /status — Show bot status
  /skills — List available skills
  $<name> — Activate a skill inline (e.g. $weather)
  /help — Show available commands
```

---

### $skill-name

```
$skill-name [message]
```

Activate a skill inline. The skill content is automatically appended to your message and the skill becomes active for that conversation.

**Arguments:**

| Argument | Description |
|----------|-------------|
| `skill-name` | Name of the skill to activate |
| `message` | Your actual message |

**Examples:**

```bash
# Get weather using $weather skill
You: $weather what's the forecast for Tokyo?

# Use memory skill to query past conversations
You: $memory what did we discuss yesterday?
```

---

## Configuration File

Nanobot uses a JSON configuration file (default: `~/.nanobot/config.json`).

### Example Configuration

```json
{
  "agents": {
    "defaults": {
      "model": "gpt-4o",
      "temperature": 0.7,
      "max_tokens": 4096,
      "workspace": "~/nanobot-workspace"
    }
  },
  "providers": {
    "openai": {
      "api_key": "sk-..."
    }
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "config": {
        "token": "..."
      }
    },
    "discord": {
      "enabled": true,
      "config": {
        "token": "..."
      }
    }
  }
}
```

---

## Environment Variables

Nanobot supports environment variables in configuration:

```json
{
  "providers": {
    "openai": {
      "api_key": "${OPENAI_API_KEY}"
    }
  }
}
```

Common environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `TELEGRAM_BOT_TOKEN` - Telegram bot token
- `DISCORD_BOT_TOKEN` - Discord bot token
