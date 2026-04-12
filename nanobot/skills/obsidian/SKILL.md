---
name: obsidian
description: Work with Obsidian vaults (plain Markdown notes) using obsidian-cli.
metadata: {"nanobot":{"emoji":"💎","requires":{"bins":["obsidian-cli"]},"install":[{"id":"brew","kind":"brew","formula":"yakitrak/yakitrak/obsidian-cli","bins":["obsidian-cli"],"label":"Install obsidian-cli (brew)"}]}}
---

# Obsidian

Obsidian vault = a normal folder on disk. Notes are plain Markdown files.

## Vault Structure

- Notes: `*.md` (plain text Markdown; edit with any editor)
- Config: `.obsidian/` (workspace + plugin settings)
- Canvases: `*.canvas` (JSON)
- Attachments: images/PDFs/etc. in your chosen attachments folder

## Find Active Vaults

Obsidian desktop tracks vaults in:
- `~/Library/Application Support/obsidian/obsidian.json` (macOS)
- `~/.config/obsidian/obsidian.json` (Linux)

The vault with `"open": true` is the active one.

## Quick Start

```bash
# Set default vault (once)
obsidian-cli set-default "vault-name"

# Print current vault path
obsidian-cli print-default --path-only
```

## Common Commands

### Search

```bash
# Search note names
obsidian-cli search "query"

# Search inside notes (shows snippets)
obsidian-cli search-content "query"
```

### Create Notes

```bash
# Create new note
obsidian-cli create "Folder/New note" --content "Hello world"

# Create with template
obsidian-cli create "notes/daily" --content "$(date +%Y-%m-%d)"
```

### Move/Rename

```bash
# Move note (updates wikilinks automatically)
obsidian-cli move "old/path/note.md" "new/path/note.md"
```

### Delete

```bash
# Delete note
obsidian-cli delete "path/note"
```

## Direct File Access

Since vaults are just folders, you can also use read_file/edit_file tools:
- Read: `read_file("~/Documents/Obsidian/Notes/my-note.md")`
- Write: `write_file("~/Documents/Obsidian/Notes/new.md", "# Content")`

## Best Practices

1. Don't hardcode vault paths - use `obsidian-cli print-default`
2. Avoid creating notes in hidden folders (`.folder/...`)
3. Use wikilinks (`[[note-name]]`) for internal links
4. Backup before bulk operations