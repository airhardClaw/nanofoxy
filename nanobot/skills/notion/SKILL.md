---
name: notion
description: Notion API for creating and managing pages, databases, and blocks via REST API.
metadata: {"nanobot":{"emoji":"📝","requires":{"env":["NOTION_API_KEY"]},"install":[{"label":"Create integration at https://notion.so/my-integrations","kind":"web"}]}}
---

# Notion

Use the Notion API to create, read, and update pages, databases, and blocks.

## Setup

1. Create an integration at https://notion.so/my-integrations
2. Copy the API key (starts with `secret_`)
3. Set environment variable: `NOTION_API_KEY`
4. Share pages/databases with your integration (click "..." → "Connect to")

## API Basics

```bash
NOTION_VERSION="2022-06-28"

# All requests need these headers
# -H "Authorization: Bearer $NOTION_API_KEY"
# -H "Notion-Version: $NOTION_VERSION"
# -H "Content-Type: application/json"
```

## Common Operations

### Search

```bash
# Search pages and databases
curl -X POST "https://api.notion.com/v1/search" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION" \
  -d '{"query": "project notes", "filter": {"property": "object", "value": "page"}}'
```

### Get Page

```bash
# Get page metadata
curl "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION"

# Get page content (blocks)
curl "https://api.notion.com/v1/blocks/{page_id}/children?page_size=100" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION"
```

### Create Page

```bash
# Create page in database
curl -X POST "https://api.notion.com/v1/pages" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION" \
  -H "Content-Type: application/json" \
  -d '{
    "parent": {"database_id": "DATABASE_ID"},
    "properties": {
      "Name": {"title": [{"text": {"content": "My Note"}}]},
      "Status": {"select": {"name": "In Progress"}}
    }
  }'
```

### Update Page

```bash
# Update page properties
curl -X PATCH "https://api.notion.com/v1/pages/{page_id}" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "Status": {"select": {"name": "Done"}}
    }
  }'
```

### Query Database

```bash
# Query database with filters
curl -X POST "https://api.notion.com/v1/databases/{database_id}/query" \
  -H "Authorization: Bearer $NOTION_API_KEY" \
  -H "Notion-Version: $NOTION_VERSION" \
  -H "Content-Type: application/json" \
  -d '{
    "filter": {"property": "Status", "select": {"equals": "In Progress"}},
    "sorts": [{"property": "Created", "direction": "descending"}]
  }'
```

## Property Types

When creating/updating pages, use these property formats:

| Type | Format |
|------|--------|
| Title | `"title": [{"text": {"content": "Title"}}]` |
| Text | `"rich_text": [{"text": {"content": "Text"}}]` |
| Select | `"select": {"name": "Option"}` |
| Multi-select | `"multi_select": [{"name": "Option1"}, {"name": "Option2"}]` |
| Checkbox | `"checkbox": true` |
| Date | `"date": {"start": "2024-01-01"}}` |
| URL | `"url": "https://example.com"` |

## Best Practices

1. Always include `Notion-Version` header
2. Use `page_size` parameter for pagination (max 100)
3. Store page IDs for later updates
4. Share databases with integration before querying