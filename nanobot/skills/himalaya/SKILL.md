---
name: himalaya
description: CLI email client for managing emails via IMAP/SMTP from the terminal.
metadata: {"nanobot":{"emoji":"📧","requires":{"bins":["himalaya"]},"install":[{"id":"brew","kind":"brew","formula":"himalaya","bins":["himalaya"],"label":"Install Himalaya (brew)"}]}}
---

# Himalaya Email CLI

CLI email client using IMAP/SMTP. Manage emails from terminal.

## Setup

```bash
# Configure account
himalaya account configure

# Or manually at ~/.config/himalaya/config.toml
```

## Quick Commands

```bash
# List accounts
himalaya account list

# List envelopes (emails)
himalaya envelope list -w 80

# Read email
himalaya envelope read <id>

# Send email
himalaya envelope send --from "you@example.com" --to "to@example.com" --subject "Subject" --body "Body"

# Delete email
himalaya envelope delete <id>

# Search
himalaya envelope search "from:boss@example.com"
```

## Flags

- `-o` output format (json, plain, table)
- `-w` column width
- `--account` specify account

## Compose with MML

```bash
echo 'To: to@example.com
Subject: Hello
Content-Type: text/plain; charset=utf-8

Hello from terminal!' | himalaya envelope send
```

## Notes

- Supports multiple accounts
- IMAP for reading, SMTP for sending
- Password stored in OS keychain