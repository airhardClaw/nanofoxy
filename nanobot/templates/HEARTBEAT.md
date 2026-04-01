# Heartbeat Tasks

This file is checked every 30 minutes by your nanobot agent.
Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

## Active Tasks

<!-- Add your periodic tasks below this line -->


## Completed

<!-- Move completed tasks here or delete them -->


## Auto-Dokumentation

Nach jedem Heartbeat werden Tasks und Ergebnisse automatisch dokumentiert:
- `memory/tasks/{datum}.md` - Aktuelle Tasks mit Results
- `memory/plans/active.md` - Aktiver Plan (wird laufend aktualisiert)

**Wichtig**: Nach dem Arbeiten an Tasks, schreibe Ergebnisse in Files!
Nutze `write_file` um wichtige Informationen zu speichern.

