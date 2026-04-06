---
name: gnome-calendar
description: Read, create, edit and delete calendar events from GNOME-connected Google calendars.
trigger_patterns:
  - "calendar"
  - "termine"
  - "event"
  - "meeting"
  - "kalender"
  - "termin"
metadata: {"nanobot":{"emoji":"📅","requires":{"bins":["python3"]}}}
---

# GNOME Calendar

Access calendar events synced through GNOME Online Accounts (Google Calendar).

## How it Works

Events are stored in GNOME's Evolution Data Server cache at `~/.cache/evolution/calendar/`. The tool reads these ICS files to list, create, edit, and delete events.

## Actions

### List Calendars
Show all available calendars:
```
calendar(action="list_calendars")
```

### List Events
List events for a specific date or date range:
```
calendar(action="list", date="2026-04-06")
calendar(action="list", date="2026-04-06", calendar_id="work")
calendar(action="list", start="2026-04-01", end="2026-04-07")
```

### Add Event
Create a new calendar event:
```
calendar(action="add", title="Team Meeting", start="2026-04-06T14:00", end="2026-04-06T15:00")
calendar(action="add", title="Lunch", start="2026-04-06T12:00", end="2026-04-06T13:00", description="With client", location="Restaurant")
```

### Edit Event
Modify an existing event (requires UID):
```
calendar(action="edit", uid="abc123", title="New Title")
```

### Delete Event
Remove an event (requires UID):
```
calendar(action="delete", uid="abc123")
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| action | string | Action: list_calendars, list, add, edit, delete |
| calendar_id | string | Calendar identifier (optional, default: all) |
| date | string | Single date (YYYY-MM-DD) |
| start | string | Start datetime (ISO format) |
| end | string | End datetime (ISO format) |
| title | string | Event title |
| description | string | Event description |
| location | string | Event location |
| uid | string | Event UID (for edit/delete) |

## Calendar IDs

Use `list_calendars` to see available calendars. Common patterns:
- Default system calendar: often "personal" or "system"
- Google calendars: identified by email or custom names

## Tips

- Use "list_calendars" first to discover available calendar IDs
- Get UID from "list" output to edit or delete specific events
- All times are in local timezone
