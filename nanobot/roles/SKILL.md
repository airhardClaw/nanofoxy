---
name: roles
description: "Weist Subagenten Rollen zu und verwaltet Team-Kommunikation. Triggers: '@coding', '@websearch', '@file', '@info', 'assign role', 'an [expert]', 'starte [role] subagent'"
trigger_patterns:
  - "@coding"
  - "@websearch"
  - "@file"
  - "@info"
  - "@information"
  - "assign role"
  - "an expert"
  - "starte"
  - "subagent"
---

# Rollen-System

Dieses Skill ermöglicht die Verwaltung und Zuweisung von Subagenten-Rollen.

## Verfügbare Rollen

| Rolle | Beschreibung | Verfügbare Tools |
|-------|---------------|-------------------|
| coding-expert | Code-Analyse und Softwareentwicklung | read_file, write_file, edit_file, list_dir, exec, web_fetch |
| websearch-expert | Internet-Recherche und Information Gathering | web_search, web_fetch, read_file, write_file |
| file-handel-expert | Dateisystem-Operationen und Verwaltung | read_file, write_file, edit_file, list_dir, list_file_backups, restore_file_backup |
| information-expert | Markdown-Files und Wissensmanagement | read_file, write_file, edit_file, list_dir, memory |

## Rollen-Zuweisung

### Trigger erkennen

Wenn der User einen Experten benötigt:
1. **@Erwähnung erkennen**: `@coding`, `@websearch`, `@file`, `@info`
2. **Aufgabe analysieren**: Was soll der Subagent tun?
3. **Passende Rolle wählen**: Basierend auf der Aufgabe

### Mapping: Aufgabe → Rolle

```
Code schreiben / debuggen / refactoren → coding-expert
Recherche / Internet-Suche / Fakten finden → websearch-expert
Dateien organisieren / Backup / Restore / File-Op → file-handel-expert
Dokumente / Notes / Markdown / Wissensbank → information-expert
```

## Subagent-Konfiguration

Die Subagent-Konfiguration liegt in `~/.nanobot/workspace/.subagents/`:

### config.json (Registry)
```json
{
  "group_chat": "-1001234567890",
  "subagents": {
    "coding_extest": { "enabled": true },
    "websearch_expert": { "enabled": true },
    "file_handel_expert": { "enabled": true },
    "information_expert": { "enabled": true }
  }
}
```

### <subagent>.json (Individuelle Config)
```json
{
  "role": "coding-expert",
  "model": "qwen2.5-7b-instruct",
  "enabled": true,
  "bot_token": "MANUELL_EINTRAGEN",
  "allowed_chats": ["-1001234567890", "DEINE_CHAT_ID"],
  "allow_from": ["DEINE_CHAT_ID"],
  "respond_to_mentions": true,
  "heartbeat": {
    "enabled": false,
    "task": "Check pending code reviews"
  },
  "memory_dir": "memory/subagents/coding_expert"
}
```

## Kommunikation

### Telegram-Gruppe

- Alle Subagenten können in einer Gruppe kommunizieren
- Erwähnung `@subagent_name` triggert den entsprechenden Subagenten
- Der Chief-Agent koordiniert die Kommunikation

### Erlaubte Chats

- Aus `allow_from` in der Subagent-Config
- Kombiniert mit `channels.allow_from` aus config.json

## Workflow: Subagent starten

1. **Parse Anfrage**:
   - Extrahiere Subagent-Namen aus @erwähnung
   - Extrahiere Aufgabe aus der Nachricht

2. **Lade Konfiguration**:
   - Lade Rolle aus `roles/<role>.md`
   - Lade Subagent-Config aus `.subagents/<subagent_id>.json`
   - Prüfe ob Subagent enabled ist

3. **Starte Subagent**:
   - Nutze `spawn` Tool mit role-parameter
   - Baue System-Prompt mit Rollen-Definition
   - Filter Tools nach Rolle

4. **Ergebnis liefern**:
   - Subagent liefert Ergebnis
   - Chief-Agent fasst zusammen für User

## Memory pro Subagent

Jeder Subagent hat eigene Memory-Dateien:
- `memory/subagents/<subagent_id>/`
- Wird bei onboard automatisch erstellt
- Subagent kann eigene Notes und Kontext speichern

## Heartbeat pro Subagent

Optional kann jeder Subagent eigene Heartbeat-Tasks haben:
- In `.subagents/<subagent>.json` konfiguriert
- `heartbeat.enabled: true` aktiviert
- `heartbeat.task` definiert die Aufgabe
- Wird parallel zum Chief-Heartbeat ausgeführt