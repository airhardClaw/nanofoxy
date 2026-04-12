---
name: gnome-calendar
description: Read, create, edit and delete calendar events from local ICS files.
trigger_patterns:
  - "calendar"
  - "termine"
  - "event"
  - "meeting"
  - "kalender"
  - "termin"
metadata: {"nanobot":{"emoji":"📅"}}
---

# GNOME Calendar

Manage calendar events using the local ICS file.

## ICS File Location

**Primary Calendar**: `/home/sir-airhard/.local/share/evolution/calendar/system/calendar.ics`

## How it Works

Events are stored in the ICS file at `/home/sir-airhard/.local/share/evolution/calendar/system/calendar.ics`. Use read_file and edit_file to manage events.

## CRITICAL: You MUST use tools

When user asks to create calendar event, you MUST:
1. FIRST read_file the ICS file
2. THEN edit_file to add the event

Do NOT just explain - actually call the tools!

### Create Event - Step by Step

Step 1: Read the calendar file:
{"tool": "read_file", "path": "/home/sir-airhard/.local/share/evolution/calendar/system/calendar.ics"}

Step 2: Edit to add event - replace "END:VCALENDAR" with event block:
{"tool": "edit_file", "path": "/home/sir-airhard/.local/share/evolution/calendar/system/calendar.ics", "old_string": "END:VCALENDAR", "new_string": "BEGIN:VEVENT\nUID:20260415@nanobot\nDTSTAMP:20260415T080000Z\nDTSTART:20260415T080000Z\nDTEND:20260415T090000Z\nSUMMARY:Blumen für meine Frau\nEND:VEVENT\nEND:VCALENDAR"}

### Delete Event
1. **Read** file to find the VEVENT block
2. **Remove** entire block using `edit_file`

### Update Event
1. **Read** file
2. **Edit** specific fields using `edit_file`

## ICS Format Reference

| Field | Required | Description |
|-------|----------|-------------|
| UID | Auto | Unique identifier (timestamp@nanobot) |
| DTSTAMP | Auto | Creation timestamp |
| DTSTART | Yes | Start time (UTC) |
| DTEND | No | End time (UTC) |
| SUMMARY | Yes | Event title |
| DESCRIPTION | No | Event details |
| LOCATION | No | Location |

## Date Format
- ICS: `YYYYMMDDTHHMMSSZ` (e.g., `20260415T143000Z`)
- Human: `2026-04-15 14:30 UTC`

## Example Workflow

1. List events: Read calendar.ics
2. Create: edit_file to insert VEVENT before END:VCALENDAR
3. Delete: Remove BEGIN:VEVENT...END:VEVENT block

## Tips

- Always use UTC (Z suffix) for times
- Generate unique UIDs: timestamp + random
