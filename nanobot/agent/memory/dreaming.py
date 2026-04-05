"""Dreaming memory consolidation - background organization, promotion, and reflection."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from loguru import logger

from nanobot.utils.helpers import ensure_dir

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider


class RecallEntry:
    """An entry in the short-term recall store."""

    def __init__(
        self,
        entry_id: str,
        query: str,
        score: float,
        timestamp: datetime | None = None,
    ):
        self.entry_id = entry_id
        self.query = query
        self.score = score
        self.timestamp = timestamp or datetime.now()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "query": self.query,
            "score": self.score,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecallEntry:
        return cls(
            entry_id=data["entry_id"],
            query=data["query"],
            score=data["score"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else None,
        )


class ShortTermRecallStore:
    """Stores recall events for promotion decisions."""

    def __init__(self, workspace: Path):
        self.dreams_dir = ensure_dir(workspace / "memory" / ".dreams")
        self.recall_file = self.dreams_dir / "short-term-recall.json"

    def _load(self) -> list[RecallEntry]:
        """Load recall entries from disk."""
        if not self.recall_file.exists():
            return []
        try:
            data = json.loads(self.recall_file.read_text(encoding="utf-8"))
            return [RecallEntry.from_dict(e) for e in data]
        except Exception:
            logger.warning("Failed to load recall store, starting fresh")
            return []

    def _save(self, entries: list[RecallEntry]) -> None:
        """Save recall entries to disk."""
        data = [e.to_dict() for e in entries]
        self.recall_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_recall(self, entry_id: str, query: str, score: float = 1.0) -> None:
        """Record a recall event."""
        entries = self._load()
        entries.append(RecallEntry(entry_id=entry_id, query=query, score=score))
        self._save(entries)

    def get_recalls(
        self,
        entry_id: str | None = None,
        since: datetime | None = None,
    ) -> list[RecallEntry]:
        """Get recall entries, optionally filtered."""
        entries = self._load()
        if entry_id:
            entries = [e for e in entries if e.entry_id == entry_id]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries

    def get_recall_stats(self, entry_id: str) -> dict[str, Any]:
        """Get recall statistics for an entry."""
        recalls = self.get_recalls(entry_id=entry_id)
        if not recalls:
            return {"count": 0, "avg_score": 0.0, "unique_queries": 0}

        queries = set(r.query for r in recalls)
        return {
            "count": len(recalls),
            "avg_score": sum(r.score for r in recalls) / len(recalls),
            "unique_queries": len(queries),
        }

    def clear_old(self, before: datetime) -> int:
        """Clear recall entries older than specified time."""
        entries = self._load()
        before = before.replace(tzinfo=None) if before.tzinfo else before
        filtered = [e for e in entries if e.timestamp.replace(tzinfo=None) >= before]
        removed = len(entries) - len(filtered)
        self._save(filtered)
        return removed


class DailyNoteManager:
    """Manages daily memory notes."""

    def __init__(self, workspace: Path, timezone: str | None = None):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.timezone = ZoneInfo(timezone) if timezone else ZoneInfo("UTC")

    def get_today_filename(self) -> Path:
        """Get the filename for today's daily note."""
        today = datetime.now(self.timezone).strftime("%Y-%m-%d")
        return self.memory_dir / f"{today}.md"

    def get_note(self, date: datetime | None = None) -> Path:
        """Get the daily note for a specific date."""
        if date:
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now(self.timezone).strftime("%Y-%m-%d")
        return self.memory_dir / f"{date_str}.md"

    def read_note(self, date: datetime | None = None) -> str:
        """Read the daily note content."""
        note_path = self.get_note(date)
        if note_path.exists():
            return note_path.read_text(encoding="utf-8")
        return ""

    def append_to_note(self, section: str, content: str, date: datetime | None = None) -> None:
        """Append content to a section in the daily note."""
        note_path = self.get_note(date)
        existing = self.read_note(date)

        section_marker = f"## {section}"
        if section_marker in existing:
            lines = existing.split("\n")
            for i, line in enumerate(lines):
                if line.strip() == section_marker.strip():
                    insert_pos = i + 1
                    while insert_pos < len(lines) and lines[insert_pos].strip():
                        insert_pos += 1
                    lines.insert(insert_pos, content.strip())
                    break
            new_content = "\n".join(lines)
        else:
            new_content = existing.rstrip() + f"\n\n{section_marker}\n\n{content.strip()}\n"

        note_path.write_text(new_content, encoding="utf-8")

    def get_recent_notes(self, days: int = 7) -> list[tuple[datetime, str]]:
        """Get recent daily notes with their content."""
        notes = []
        today = datetime.now(self.timezone)
        for i in range(days):
            date = today - timedelta(days=i)
            content = self.read_note(date)
            if content:
                notes.append((date, content))
        return notes


class PromotionTracker:
    """Tracks which entries have been promoted to durable memory."""

    def __init__(self, workspace: Path):
        self.dreams_dir = ensure_dir(workspace / "memory" / ".dreams")
        self.promoted_file = self.dreams_dir / "promoted.json"

    def _load(self) -> dict[str, datetime]:
        """Load promoted entries."""
        if not self.promoted_file.exists():
            return {}
        try:
            data = json.loads(self.promoted_file.read_text(encoding="utf-8"))
            return {k: datetime.fromisoformat(v) for k, v in data.items()}
        except Exception:
            return {}

    def _save(self, data: dict[str, datetime]) -> None:
        """Save promoted entries."""
        self.promoted_file.write_text(
            json.dumps({k: v.isoformat() for k, v in data.items()}, indent=2),
            encoding="utf-8"
        )

    def mark_promoted(self, entry_id: str) -> None:
        """Mark an entry as promoted."""
        data = self._load()
        data[entry_id] = datetime.now()
        self._save(data)

    def is_promoted(self, entry_id: str) -> bool:
        """Check if an entry has been promoted."""
        return entry_id in self._load()

    def get_promoted_count(self) -> int:
        """Get count of promoted entries."""
        return len(self._load())


class DreamingService:
    """Main dreaming service coordinating Light, Deep, and REM phases."""

    def __init__(
        self,
        workspace: Path,
        provider: "LLMProvider",
        model: str,
        config: dict[str, Any] | None = None,
    ):
        self.workspace = workspace
        self.provider = provider
        self.model = model
        self.config = config or {}

        self.timezone = self.config.get("timezone")
        self.verbose = self.config.get("verboseLogging", False)

        self.recall_store = ShortTermRecallStore(workspace)
        self.daily_notes = DailyNoteManager(workspace, self.timezone)
        self.promotion_tracker = PromotionTracker(workspace)

        self._light_config = self.config.get("light", {})
        self._deep_config = self.config.get("deep", {})
        self._rem_config = self.config.get("rem", {})

    @property
    def enabled(self) -> bool:
        """Check if dreaming is enabled."""
        return self.config.get("enabled", True)

    async def run_light_phase(self) -> int:
        """Run Light phase - organize and stage candidates."""
        if not self.enabled or not self._light_config.get("enabled", True):
            return 0

        lookback = self._light_config.get("lookbackDays", 2)
        limit = self._light_config.get("limit", 100)
        dedupe_thresh = self._light_config.get("dedupeSimilarity", 0.9)

        since = datetime.now() - timedelta(days=lookback)
        all_recalls = self.recall_store.get_recalls(since=since)

        candidates = self._dedupe_and_rank(all_recalls, dedupe_thresh, limit)

        if candidates:
            content = "\n\n".join(f"- {c.entry_id}: {c.query} (score: {c.score:.2f})" for c in candidates)
            self.daily_notes.append_to_note("Light Sleep", content)
            logger.info("Light phase: staged {} candidates", len(candidates))

        return len(candidates)

    async def run_deep_phase(self) -> int:
        """Run Deep phase - promote candidates to durable memory."""
        if not self.enabled or not self._deep_config.get("enabled", True):
            return 0

        lookback = self._deep_config.get("lookbackDays", 30)
        limit = self._deep_config.get("limit", 10)
        min_score = self._deep_config.get("minScore", 0.8)
        min_recalls = self._deep_config.get("minRecallCount", 3)
        min_queries = self._deep_config.get("minUniqueQueries", 3)

        since = datetime.now() - timedelta(days=lookback)
        all_recalls = self.recall_store.get_recalls(since=since)

        entry_ids = set(r.entry_id for r in all_recalls)
        candidates = []

        for entry_id in entry_ids:
            stats = self.recall_store.get_recall_stats(entry_id)

            if stats["count"] < min_recalls:
                continue
            if stats["unique_queries"] < min_queries:
                continue

            score = self._calculate_promotion_score(stats, lookback)
            if score >= min_score and not self.promotion_tracker.is_promoted(entry_id):
                candidates.append((entry_id, score))

        candidates.sort(key=lambda x: x[1], reverse=True)
        promoted = candidates[:limit]

        promoted_count = 0
        for entry_id, score in promoted:
            self.promotion_tracker.mark_promoted(entry_id)
            promoted_count += 1
            logger.info("Deep phase: promoted {} (score: {:.2f})", entry_id, score)

        logger.info("Deep phase: promoted {} entries", promoted_count)
        return promoted_count

    async def run_rem_phase(self) -> int:
        """Run REM phase - detect patterns and write reflections."""
        if not self.enabled or not self._rem_config.get("enabled", True):
            return 0

        lookback = self._rem_config.get("lookbackDays", 7)
        limit = self._rem_config.get("limit", 10)
        min_strength = self._rem_config.get("minPatternStrength", 0.75)

        notes = self.daily_notes.get_recent_notes(lookback)

        themes = self._detect_themes(notes, min_strength, limit)

        if themes:
            content = "\n\n".join(f"- {t}" for t in themes)
            self.daily_notes.append_to_note("REM Sleep", content)
            logger.info("REM phase: detected {} themes", len(themes))

        return len(themes)

    def _dedupe_and_rank(
        self,
        recalls: list[RecallEntry],
        similarity_threshold: float,
        limit: int,
    ) -> list[RecallEntry]:
        """Deduplicate recalls by Jaccard similarity and rank by score."""
        if not recalls:
            return []

        unique_entries = {}
        for r in recalls:
            if r.entry_id not in unique_entries:
                unique_entries[r.entry_id] = []
            unique_entries[r.entry_id].append(r)

        ranked = []
        for entry_id, recs in unique_entries.items():
            avg_score = sum(r.score for r in recs) / len(recs)
            ranked.append(RecallEntry(entry_id, recs[0].query, avg_score))

        ranked.sort(key=lambda x: x.score, reverse=True)
        return ranked[:limit]

    def _calculate_promotion_score(self, stats: dict[str, Any], lookback_days: int) -> float:
        """Calculate weighted promotion score using six signals."""
        weights = {
            "frequency": 0.24,
            "relevance": 0.30,
            "query_diversity": 0.15,
            "recency": 0.15,
            "consolidation": 0.10,
            "conceptual_richness": 0.06,
        }

        count = stats["count"]
        avg_score = stats["avg_score"]
        unique_queries = stats["unique_queries"]

        frequency = min(count / 10, 1.0)
        relevance = avg_score
        query_diversity = min(unique_queries / 5, 1.0)
        recency = 0.5
        consolidation = min(count / 5, 1.0)
        conceptual_richness = min(unique_queries / 3, 1.0)

        score = (
            weights["frequency"] * frequency +
            weights["relevance"] * relevance +
            weights["query_diversity"] * query_diversity +
            weights["recency"] * recency +
            weights["consolidation"] * consolidation +
            weights["conceptual_richness"] * conceptual_richness
        )

        return score

    def _detect_themes(
        self,
        notes: list[tuple[datetime, str]],
        min_strength: float,
        limit: int,
    ) -> list[str]:
        """Detect recurring themes from daily notes."""
        tag_counts: dict[str, int] = {}

        for _, content in notes:
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-") and ":" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        tag = parts[0].strip().lstrip("-").strip()
                        if tag:
                            tag_counts[tag] = tag_counts.get(tag, 0) + 1

        total_notes = len(notes) if notes else 1
        themes = [
            f"{tag} (appeared {count} times)"
            for tag, count in tag_counts.items()
            if count / total_notes >= min_strength
        ]

        return themes[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get dreaming statistics."""
        return {
            "short_term_recalls": len(self.recall_store._load()),
            "promoted_count": self.promotion_tracker.get_promoted_count(),
            "enabled": self.enabled,
        }


if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider