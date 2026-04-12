---
name: slack
description: Send messages, reactions, and manage Slack via the message tool with channel=slack.
metadata: {"nanobot":{"emoji":"💬","requires":{"config":["channels.slack.token"]}}}
---

# Slack

Use the `message` tool with `channel: "slack"` for Slack operations.

## Setup

Configure Slack bot token in config:
```yaml
channels:
  slack:
    token: "xoxb-..."
```

## Common Actions

### Send Message

```json
{
  "action": "send",
  "channel": "slack",
  "to": "channel:C123456",
  "message": "Hello team!"
}
```

### Send to User (DM)

```json
{
  "action": "send",
  "channel": "slack",
  "to": "user:U123456",
  "message": "Hey!"
}
```

### React to Message

Slack message IDs appear in the format `1712023032.1234`:
```json
{
  "action": "react",
  "channel": "slack",
  "channelId": "C123456",
  "messageId": "1712023032.1234",
  "emoji": "✅"
}
```

### Pin/Unpin

```json
{
  "action": "pin",
  "channel": "slack",
  "channelId": "C123456",
  "messageId": "1712023032.1234"
}
```

```json
{
  "action": "unpin",
  "channel": "slack",
  "channelId": "C123456",
  "messageId": "1712023032.1234"
}
```

### Edit Message

```json
{
  "action": "edit",
  "channel": "slack",
  "channelId": "C123456",
  "messageId": "1712023032.1234",
  "message": "Updated text"
}
```

## Format Notes

- Mention users: `<@U123456>`
- Mention channels: `<#C123456>`
- Links: `<https://example.com|text>`
- Avoid Markdown tables (use code blocks)