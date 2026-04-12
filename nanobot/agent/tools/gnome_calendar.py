"""GNOME Calendar tool for reading and managing calendar events."""

import re
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool

CALENDAR_CACHE_DIR = Path.home() / ".cache" / "evolution" / "calendar"


class GNOMECalendarTool(Tool):
    """Tool to interact with GNOME Calendar (synced Google Calendar)."""

    def __init__(self):
        self._cache_dir = CALENDAR_CACHE_DIR

    @property
    def name(self) -> str:
        return "calendar"

    @property
    def description(self) -> str:
        return (
            "Read, create, edit and delete calendar events from GNOME-connected calendars. "
            "Use list_calendars to see available calendars, list to view events, "
            "add to create events, edit to modify, delete to remove."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list_calendars", "list", "add", "edit", "delete"],
                    "description": "Action to perform",
                },
                "calendar_id": {
                    "type": "string",
                    "description": "Calendar identifier (use list_calendars to find IDs)",
                },
                "date": {
                    "type": "string",
                    "description": "Single date for listing events (YYYY-MM-DD)",
                },
                "start": {
                    "type": "string",
                    "description": "Start datetime for new event (ISO format: YYYY-MM-DDTHH:MM)",
                },
                "end": {
                    "type": "string",
                    "description": "End datetime for new event (ISO format: YYYY-MM-DDTHH:MM)",
                },
                "title": {
                    "type": "string",
                    "description": "Event title",
                },
                "description": {
                    "type": "string",
                    "description": "Event description",
                },
                "location": {
                    "type": "string",
                    "description": "Event location",
                },
                "uid": {
                    "type": "string",
                    "description": "Event UID (required for edit/delete)",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        calendar_id: str | None = None,
        date: str | None = None,
        start: str | None = None,
        end: str | None = None,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
        uid: str | None = None,
        **kwargs: Any,
    ) -> str:
        if action == "list_calendars":
            return self._list_calendars()
        elif action == "list":
            return self._list_events(calendar_id, date)
        elif action == "add":
            return self._add_event(calendar_id, title, start, end, description, location)
        elif action == "edit":
            return self._edit_event(calendar_id, uid, title, start, end, description, location)
        elif action == "delete":
            return self._delete_event(calendar_id, uid)
        return f"Unknown action: {action}"

    def _get_calendar_name(self, calendar_id: str) -> str:
        """Try to get calendar name from the database."""
        try:
            db_path = self._cache_dir / calendar_id / "cache.db"
            if not db_path.exists():
                return calendar_id

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Try to get any event to extract calendar name
            cursor.execute("SELECT ECacheOBJ FROM ECacheObjects LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                ics_data = row[0]
                if "X-WR-CALNAME" in ics_data:
                    import re
                    match = re.search(r"X-WR-CALNAME:(.+?)(?:\r?\n|\Z)", ics_data)
                    if match:
                        return match.group(1).strip()
        except Exception:
            pass
        return calendar_id

    def _list_calendars(self) -> str:
        if not self._cache_dir.exists():
            return f"Calendar cache not found at {self._cache_dir}. Is GNOME Calendar configured?"

        calendars = []
        for cal_dir in self._cache_dir.iterdir():
            if cal_dir.is_dir() and cal_dir.name not in ("trash",):
                cal_name = self._get_calendar_name(cal_dir.name)
                calendars.append(f"- {cal_name} (id: {cal_dir.name})")

        if not calendars:
            return "No calendars found. Make sure GNOME Calendar is set up and synced."
        return "Available calendars:\n" + "\n".join(calendars)

    def _parse_ics_datetime(self, ics_data: str, field: str) -> tuple[Any, Any]:
        """Parse DTSTART and DTEND from ICS data."""
        dtstart = None
        dtend = None

        # Handle DATE (all-day events): DTSTART;VALUE=DATE:20260501
        match = re.search(rf"{field};VALUE=DATE:(\d{{8}})", ics_data)
        if match:
            dt_val = match.group(1)
            dtstart = datetime.strptime(dt_val, "%Y%m%d").date()

            # Try DTEND
            end_match = re.search(r"DTEND;VALUE=DATE:(\d{8})", ics_data)
            if end_match:
                dtend = datetime.strptime(end_match.group(1), "%Y%m%d").date()
            return dtstart, dtend

        # Handle datetime with TZID: DTSTART;TZID=Europe/Vienna:20260406T143000
        match = re.search(rf"{field};TZID=[^:]+:(\d{{4}})(\d{{2}})(\d{{2}}T\d{{2}})\d{{2}}", ics_data)
        if match:
            dt_val = f"{match.group(1)}-{match.group(2)}-{match.group(3)}".replace("T", " ")
            dtstart = datetime.strptime(dt_val, "%Y-%m-%d %H%M")

        # Handle datetime without TZ (UTC): DTSTART:20260406T143000Z
        if not dtstart:
            match = re.search(rf"{field}:(\d{{4}})(\d{{2}})(\d{{2}}T\d{{2}})\d{{2}}([Z+-])?", ics_data)
            if match:
                dt_val = f"{match.group(1)}-{match.group(2)}-{match.group(3)}".replace("T", " ")
                dtstart = datetime.strptime(dt_val, "%Y-%m-%d %H%M")

        # Parse DTEND similarly
        end_match = re.search(r"DTEND;TZID=[^:]+:(\d{4})(\d{2})(\d{2}T\d{2})\d{2}", ics_data)
        if end_match:
            dt_val = f"{end_match.group(1)}-{end_match.group(2)}-{end_match.group(3)}".replace("T", " ")
            dtend = datetime.strptime(dt_val, "%Y-%m-%d %H%M")
        elif not dtend:
            end_match = re.search(r"DTEND:(\d{4})(\d{2})(\d{2}T\d{2})\d{2}([Z+-])?", ics_data)
            if end_match:
                dt_val = f"{end_match.group(1)}-{end_match.group(2)}-{end_match.group(3)}".replace("T", " ")
                dtend = datetime.strptime(dt_val, "%Y-%m-%d %H%M")

        return dtstart, dtend

    def _list_events(self, calendar_id: str | None, date_str: str | None) -> str:
        if not self._cache_dir.exists():
            return f"Calendar cache not found at {self._cache_dir}"

        target_date = None
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return f"Invalid date format: {date_str}. Use YYYY-MM-DD"

        calendar_dirs = [self._cache_dir / calendar_id] if calendar_id else [
            d for d in self._cache_dir.iterdir() if d.is_dir() and d.name != "trash"
        ]

        events = []
        for cal_dir in calendar_dirs:
            db_path = cal_dir / "cache.db"
            if not db_path.exists():
                continue

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT ECacheUID, summary, ECacheOBJ FROM ECacheObjects")

                for row in cursor.fetchall():
                    uid, summary, ics_data = row
                    if not ics_data:
                        continue

                    dtstart, dtend = self._parse_ics_datetime(ics_data, "DTSTART")

                    if target_date:
                        if isinstance(dtstart, datetime):
                            event_date = dtstart.date()
                        elif isinstance(dtstart, date):
                            event_date = dtstart
                        else:
                            continue
                        if event_date != target_date:
                            continue

                    summary = summary or "Untitled"
                    loc_match = re.search(r"LOCATION:(.+?)(?:\r?\n|\Z)", ics_data)
                    location = loc_match.group(1).strip() if loc_match else ""

                    start_str = ""
                    if dtstart:
                        if isinstance(dtstart, datetime):
                            start_str = dtstart.strftime("%H:%M")
                        elif isinstance(dtstart, date):
                            start_str = str(dtstart)

                    end_str = ""
                    if dtend:
                        if isinstance(dtend, datetime):
                            end_str = dtend.strftime("%H:%M")
                        elif isinstance(dtend, date):
                            end_str = str(dtend)

                    time_range = f"{start_str}" + (f" - {end_str}" if end_str else "")
                    line = f"- {time_range}: {summary}"
                    if location:
                        line += f" @ {location}"
                    line += f" [uid: {uid}]"
                    events.append(line)

                conn.close()
            except Exception as e:
                events.append(f"- Error reading {cal_dir.name}: {e}")

        if not events:
            if target_date:
                return f"No events found on {target_date}"
            return "No events found"
        return "Calendar events:\n" + "\n".join(events)

    def _add_event(
        self,
        calendar_id: str | None,
        title: str | None,
        start: str | None,
        end: str | None,
        description: str | None,
        location: str | None,
    ) -> str:
        if not title:
            return "Error: title is required for add"
        if not start:
            return "Error: start datetime is required for add"

        try:
            import icalendar
        except ImportError:
            return "Error: icalendar package not installed. Install with: pip install icalendar"

        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            return f"Invalid start format: {start}. Use ISO format like 2026-04-06T14:00"

        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else start_dt

        import uuid
        event_uid = str(uuid.uuid4()) + "@nanofoxy"

        event = icalendar.Event()
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        event.add("summary", title)
        event.add("uid", event_uid)
        if description:
            event.add("description", description)
        if location:
            event.add("location", location)

        target_dir = self._cache_dir / (calendar_id or "new_calendar")
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / "cache.db"

        ics_content = event.to_ical().decode()

        if target_file.exists():
            conn = sqlite3.connect(target_file)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ECacheObjects (ECacheUID, ECacheREV, ECacheOBJ, ECacheState, summary, description, location, has_start, has_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event_uid, "1", ics_content, 0, title, description or "", location or "", 1, 1)
            )
            conn.commit()
            conn.close()
        else:
            conn = sqlite3.connect(target_file)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ECacheKeys (
                    ECacheUID TEXT PRIMARY KEY,
                    ECacheREV TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ECacheObjects (
                    ECacheUID TEXT PRIMARY KEY,
                    ECacheREV TEXT,
                    ECacheOBJ TEXT,
                    ECacheState INTEGER,
                    occur_start TEXT,
                    occur_end TEXT,
                    due TEXT,
                    completed TEXT,
                    summary TEXT,
                    comment TEXT,
                    description TEXT,
                    location TEXT,
                    attendees TEXT,
                    organizer TEXT,
                    classification TEXT,
                    status TEXT,
                    priority INTEGER,
                    percent_complete INTEGER,
                    categories TEXT,
                    has_alarm INTEGER,
                    has_attachment INTEGER,
                    has_start INTEGER,
                    has_end INTEGER,
                    has_due INTEGER,
                    has_duration INTEGER,
                    has_recurrences INTEGER,
                    bdata TEXT,
                    custom_flags INTEGER
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timezones (
                    tzid TEXT PRIMARY KEY,
                    icaldata TEXT
                )
            """)
            cursor.execute(
                "INSERT INTO ECacheObjects (ECacheUID, ECacheREV, ECacheOBJ, ECacheState, summary, description, location, has_start, has_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (event_uid, "1", ics_content, 0, title, description or "", location or "", 1, 1)
            )
            conn.commit()
            conn.close()

        return f"Created event '{title}' (uid: {event_uid}) in calendar {calendar_id or 'new_calendar'}"

    def _edit_event(
        self,
        calendar_id: str | None,
        uid: str | None,
        title: str | None,
        start: str | None,
        end: str | None,
        description: str | None,
        location: str | None,
    ) -> str:
        if not uid:
            return "Error: uid is required for edit"
        if not calendar_id:
            return "Error: calendar_id is required for edit"

        target_file = self._cache_dir / calendar_id / "cache.db"
        if not target_file.exists():
            return f"Calendar {calendar_id} not found"

        try:
            conn = sqlite3.connect(target_file)
            cursor = conn.cursor()

            # Get existing event
            cursor.execute("SELECT ECacheOBJ, summary FROM ECacheObjects WHERE ECacheUID = ?", (uid,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return f"Event with uid {uid} not found"

            ics_data, old_summary = row

            # Build updated ICS
            import icalendar
            event = icalendar.Event.from_ical(ics_data)

            if title:
                event.add("summary", title)
            if start:
                event.add("dtstart", datetime.fromisoformat(start.replace("Z", "+00:00")))
            if end:
                event.add("dtend", datetime.fromisoformat(end.replace("Z", "+00:00")))
            if description:
                event.add("description", description)
            if location:
                event.add("location", location)

            new_ics = event.to_ical().decode()
            new_summary = title or old_summary

            cursor.execute(
                "UPDATE ECacheObjects SET ECacheOBJ = ?, summary = ? WHERE ECacheUID = ?",
                (new_ics, new_summary, uid)
            )
            conn.commit()
            conn.close()
            return f"Updated event {uid}"

        except Exception as e:
            return f"Error editing event: {e}"

    def _delete_event(self, calendar_id: str | None, uid: str | None) -> str:
        if not uid:
            return "Error: uid is required for delete"
        if not calendar_id:
            return "Error: calendar_id is required for delete"

        target_file = self._cache_dir / calendar_id / "cache.db"
        if not target_file.exists():
            return f"Calendar {calendar_id} not found"

        try:
            conn = sqlite3.connect(target_file)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM ECacheObjects WHERE ECacheUID = ?", (uid,))
            if cursor.rowcount == 0:
                conn.close()
                return f"Event with uid {uid} not found"

            conn.commit()
            conn.close()
            return f"Deleted event {uid}"

        except Exception as e:
            return f"Error deleting event: {e}"
