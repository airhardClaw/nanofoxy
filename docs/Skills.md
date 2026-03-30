# Skills

Skills are markdown files that teach the agent new capabilities. They provide instructions, examples, and metadata that the agent uses to understand how to use specific features.

## Overview

Skills are located in the `skills/` directory and loaded by the `SkillsLoader` class in `agent/skills.py`.

## Skill Structure

Each skill is a markdown file (`.md`) with YAML frontmatter containing metadata.

### Frontmatter Format

```yaml
---
name: skill-name
description: What the skill does
nanobot:
  always: false  # Whether to always load this skill
  requirements:  # Optional requirements
    - some_package
---
```

### Skill Content

The markdown body contains:
- Description of what the skill does
- Usage examples
- Parameters and their meanings
- Best practices

---

## Available Skills

| Skill | Description |
|-------|-------------|
| `weather` | Get current weather information |
| `memory` | Query and manage agent memory |
| `cron` | Schedule reminders and recurring tasks |
| `summarize` | Summarize long content |
| `tmux` | Interact with tmux sessions |
| `github` | Interact with GitHub (issues, PRs, etc.) |
| `clawhub` | ClawHub integration |
| `skill-creator` | Create new skills |

---

## Skill Details

### Weather Skill

**File:** `skills/weather/SKILL.md`

Provides weather information using weather APIs.

### Memory Skill

**File:** `skills/memory/SKILL.md`

Allows the agent to query and manage its own memory (MEMORY.md, HISTORY.md).

### Cron Skill

**File:** `skills/cron/SKILL.md`

Enables scheduling reminders and recurring tasks.

### Summarize Skill

**File:** `skills/summarize/SKILL.md`

Summarizes long content using the LLM.

### Tmux Skill

**File:** `skills/tmux/SKILL.md`

Interacts with tmux sessions (create, attach, list, etc.).

### GitHub Skill

**File:** `skills/github/SKILL.md`

Interacts with GitHub API (issues, pull requests, repos, etc.).

### ClawHub Skill

**File:** `skills/clawhub/SKILL.md`

ClawHub integration for remote agent control.

### Skill Creator Skill

**File:** `skills/skill-creator/SKILL.md`

Helps create new skills with proper structure.

---

## Loading Skills

### Automatic Loading

Skills marked with `always: true` in frontmatter are always loaded.

### Context Loading

Skills can be loaded for specific contexts using the agent's skill loading mechanism.

### Listing Skills

```
Agent: /skills
```

Shows all available skills.

---

## Creating a New Skill

1. Create a new directory in `skills/`
2. Add a `SKILL.md` file with:
   - YAML frontmatter with name, description
   - Markdown body with instructions and examples
3. The agent will automatically discover it

### Example Skill

```yaml
---
name: example
description: An example skill
nanobot:
  always: false
---
# Example Skill

This skill does something useful.

## Usage

To use this skill, say "example [args]"

## Examples

- "example foo" - Does foo
- "example bar" - Does bar
```
