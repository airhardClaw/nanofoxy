"""Cron service for scheduling agent tasks."""

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine

from loguru import logger

from nanobot.cron.types import (
    CronJob,
    CronJobState,
    CronPayload,
    CronRunRecord,
    CronSchedule,
    CronStore,
)


def _now_seconds() -> int:
    return int(time.time())


def _compute_next_run(schedule: CronSchedule, now_seconds: int) -> int | None:
    """Compute next run time in seconds."""
    if schedule.kind == "at":
        return schedule.at_seconds if schedule.at_seconds and schedule.at_seconds > now_seconds else None

    if schedule.kind == "every":
        if not schedule.every_seconds or schedule.every_seconds <= 0:
            return None
        return now_seconds + schedule.every_seconds

    if schedule.kind == "cron" and schedule.expr:
        try:
            from zoneinfo import ZoneInfo

            from croniter import croniter
            base_time = now_seconds
            tz = ZoneInfo(schedule.tz) if schedule.tz else datetime.now().astimezone().tzinfo
            base_dt = datetime.fromtimestamp(base_time, tz=tz)
            cron = croniter(schedule.expr, base_dt)
            next_dt = cron.get_next(datetime)
            return int(next_dt.timestamp())
        except Exception:
            return None

    return None


def _validate_schedule_for_add(schedule: CronSchedule) -> None:
    """Validate schedule fields that would otherwise create non-runnable jobs."""
    if schedule.tz and schedule.kind != "cron":
        raise ValueError("tz can only be used with cron schedules")

    if schedule.kind == "cron" and schedule.tz:
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(schedule.tz)
        except Exception:
            raise ValueError(f"unknown timezone '{schedule.tz}'") from None


class CronService:
    """Service for managing and executing scheduled jobs."""

    _MAX_RUN_HISTORY = 20

    def __init__(
        self,
        store_path: Path,
        on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None = None,
    ):
        self.store_path = store_path
        self.on_job = on_job
        self._store: CronStore | None = None
        self._last_mtime: float = 0.0
        self._timer_task: asyncio.Task | None = None
        self._running = False

    def _migrate_short_keys(self, j: dict) -> dict:
        """Migrate from millisecond keys to seconds keys.
        
        Legacy format used milliseconds (atMs, everyMs, nextRunAtMs, etc.)
        Current format uses seconds (atS, everyS, nextRunAtS, etc.)
        
        Also fixes corrupted values where "S" suffix keys were incorrectly divided by 1000.
        """
        import copy
        j = copy.deepcopy(j)
        
        schedule = j.get("schedule", {})
        
        # atMs (milliseconds) -> atS (seconds)
        if "atMs" in schedule and schedule["atMs"] is not None:
            schedule["atS"] = schedule.pop("atMs") // 1000
        elif "atSeconds" in schedule and schedule["atSeconds"] is not None:
            schedule["atS"] = schedule.pop("atSeconds")
        
        # everyMs (milliseconds) -> everyS (seconds)
        if "everyMs" in schedule and schedule["everyMs"] is not None:
            schedule["everyS"] = schedule.pop("everyMs") // 1000
        elif "everySeconds" in schedule and schedule["everySeconds"] is not None:
            schedule["everyS"] = schedule.pop("everySeconds")
        
        state = j.get("state", {})
        
        # nextRunAtMs (milliseconds) -> nextRunAtS (seconds)
        if "nextRunAtMs" in state and state["nextRunAtMs"] is not None:
            state["nextRunAtS"] = state.pop("nextRunAtMs") // 1000
        elif "nextRunAtSeconds" in state and state["nextRunAtSeconds"] is not None:
            state["nextRunAtS"] = state.pop("nextRunAtSeconds")
        elif "nextRunAtS" in state and state["nextRunAtS"] is not None and state["nextRunAtS"] < 1000000000:
            # Corrupted: value was incorrectly divided by 1000, reverse it
            state["nextRunAtS"] = state["nextRunAtS"] * 1000
        
        # lastRunAtMs (milliseconds) -> lastRunAtS (seconds)
        if "lastRunAtMs" in state and state["lastRunAtMs"] is not None:
            state["lastRunAtS"] = state.pop("lastRunAtMs") // 1000
        elif "lastRunAtSeconds" in state and state["lastRunAtSeconds"] is not None:
            state["lastRunAtS"] = state.pop("lastRunAtSeconds")
        elif "lastRunAtS" in state and state["lastRunAtS"] is not None and state["lastRunAtS"] < 1000000000:
            # Corrupted: value was incorrectly divided by 1000, reverse it
            state["lastRunAtS"] = state["lastRunAtS"] * 1000
            
        history = state.get("runHistory", [])
        for r in history:
            # runAtMs (milliseconds) -> runAtS (seconds)
            if "runAtMs" in r and r["runAtMs"] is not None:
                r["runAtS"] = r.pop("runAtMs") // 1000
            elif "runAtSeconds" in r and r["runAtSeconds"] is not None:
                r["runAtS"] = r.pop("runAtSeconds")
            elif "runAtS" in r and r["runAtS"] is not None and r["runAtS"] < 1000000000:
                # Corrupted: value was incorrectly divided by 1000, reverse it
                r["runAtS"] = r["runAtS"] * 1000
        
        # createdAtMs (milliseconds) -> createdAtS (seconds)
        if "createdAtMs" in j and j["createdAtMs"] is not None:
            j["createdAtS"] = j.pop("createdAtMs") // 1000
        elif "createdAtSeconds" in j and j["createdAtSeconds"] is not None:
            j["createdAtS"] = j.pop("createdAtSeconds")
        elif "createdAtS" in j and j["createdAtS"] is not None and j["createdAtS"] < 1000000000:
            # Corrupted: value was incorrectly divided by 1000, reverse it
            j["createdAtS"] = j["createdAtS"] * 1000
        
        # updatedAtMs (milliseconds) -> updatedAtS (seconds)
        if "updatedAtMs" in j and j["updatedAtMs"] is not None:
            j["updatedAtS"] = j.pop("updatedAtMs") // 1000
        elif "updatedAtSeconds" in j and j["updatedAtSeconds"] is not None:
            j["updatedAtS"] = j.pop("updatedAtSeconds")
        elif "updatedAtS" in j and j["updatedAtS"] is not None and j["updatedAtS"] < 1000000000:
            # Corrupted: value was incorrectly divided by 1000, reverse it
            j["updatedAtS"] = j["updatedAtS"] * 1000
        
        return j

    def _needs_migration(self, j: dict) -> bool:
        """Check if job needs migration from milliseconds to seconds format.
        
        Migration is needed when:
        1. Legacy "Ms" or "Seconds" suffix keys exist, OR
        2. Values look corrupted (too small to be valid Unix timestamps in seconds)
        """
        schedule = j.get("schedule", {})
        if any(k in schedule for k in ["atMs", "atSeconds", "everyMs", "everySeconds"]):
            return True
        state = j.get("state", {})
        if any(k in state for k in ["nextRunAtMs", "nextRunAtSeconds", "lastRunAtMs", "lastRunAtSeconds"]):
            return True
        history = state.get("runHistory", [])
        for r in history:
            if any(k in r for k in ["runAtMs", "runAtSeconds"]):
                return True
        if any(k in j for k in ["createdAtMs", "createdAtSeconds", "updatedAtMs", "updatedAtSeconds"]):
            return True
        
        # Also check for corrupted "S" suffix values (divided by 1000 incorrectly)
        # Valid Unix timestamp in seconds should be > 1 billion (year ~2001)
        # If nextRunAtS or lastRunAtS < 1000000000, they were likely corrupted
        # (original ms value was divided by 1000, turning e.g. 1776098000000 into 1776098000)
        if state.get("nextRunAtS") is not None and state.get("nextRunAtS", 0) < 1000000000:
            return True
        if state.get("lastRunAtS") is not None and state.get("lastRunAtS", 0) < 1000000000:
            return True
        
        return False

    def _load_store(self) -> CronStore:
        """Load jobs from disk. Reloads automatically if file was modified externally."""
        if self._store and self.store_path.exists():
            mtime = self.store_path.stat().st_mtime
            if mtime != self._last_mtime:
                logger.info("Cron: jobs.json modified externally, reloading")
                self._store = None
        if self._store:
            return self._store

        if self.store_path.exists():
            try:
                data = json.loads(self.store_path.read_text(encoding="utf-8"))
                jobs = []
                migrated = False
                for j in data.get("jobs", []):
                    # Add null checks for required fields
                    if not j.get("id") or not j.get("name"):
                        continue
                    schedule_data = j.get("schedule", {})
                    if not schedule_data:
                        continue

                    # Migrate from ms/short keys to full seconds keys if needed
                    if self._needs_migration(j):
                        j = self._migrate_short_keys(j)
                        migrated = True

                    jobs.append(CronJob(
                        id=j["id"],
                        name=j["name"],
                        enabled=j.get("enabled", True),
                        schedule=CronSchedule(
                            kind=schedule_data.get("kind", "once"),
                            at_seconds=schedule_data.get("atS"),
                            every_seconds=schedule_data.get("everyS"),
                            expr=schedule_data.get("expr"),
                            tz=schedule_data.get("tz"),
                        ),
                        payload=CronPayload(
                            kind=j["payload"].get("kind", "agent_turn"),
                            message=j["payload"].get("message", ""),
                            deliver=j["payload"].get("deliver", False),
                            channel=j["payload"].get("channel"),
                            to=j["payload"].get("to"),
                        ),
                        state=CronJobState(
                            next_run_at_seconds=j.get("state", {}).get("nextRunAtS"),
                            last_run_at_seconds=j.get("state", {}).get("lastRunAtS"),
                            last_status=j.get("state", {}).get("lastStatus"),
                            last_error=j.get("state", {}).get("lastError"),
                            run_history=[
                                CronRunRecord(
                                    run_at_seconds=r.get("runAtS", 0),
                                    status=r.get("status"),
                                    duration_seconds=r.get("durationS", 0),
                                    error=r.get("error"),
                                )
                                for r in j.get("state", {}).get("runHistory", [])
                            ],
                        ),
                        created_at_seconds=j.get("createdAtS", 0),
                        updated_at_seconds=j.get("updatedAtS", 0),
                        delete_after_run=j.get("deleteAfterRun", False),
                    ))
                
                self._store = CronStore(jobs=jobs)
                
                # Save if we migrated data to disk
                if migrated:
                    logger.info("Cron: migrated jobs.json from ms to seconds format")
                    self._save_store()
            except Exception as e:
                logger.warning("Failed to load cron store: {}", e)
                self._store = CronStore()
        else:
            self._store = CronStore()

        return self._store

    def _save_store(self) -> None:
        """Save jobs to disk."""
        if not self._store:
            return

        self.store_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self._store.version,
            "jobs": [
                {
                    "id": j.id,
                    "name": j.name,
                    "enabled": j.enabled,
                    "schedule": {
                        "kind": j.schedule.kind,
                        "atS": j.schedule.at_seconds,
                        "everyS": j.schedule.every_seconds,
                        "expr": j.schedule.expr,
                        "tz": j.schedule.tz,
                    },
                    "payload": {
                        "kind": j.payload.kind,
                        "message": j.payload.message,
                        "deliver": j.payload.deliver,
                        "channel": j.payload.channel,
                        "to": j.payload.to,
                    },
                    "state": {
                        "nextRunAtS": j.state.next_run_at_seconds,
                        "lastRunAtS": j.state.last_run_at_seconds,
                        "lastStatus": j.state.last_status,
                        "lastError": j.state.last_error,
                        "runHistory": [
                            {
                                "runAtS": r.run_at_seconds,
                                "status": r.status,
                                "durationS": r.duration_seconds,
                                "error": r.error,
                            }
                            for r in j.state.run_history
                        ],
                    },
                    "createdAtS": j.created_at_seconds,
                    "updatedAtS": j.updated_at_seconds,
                    "deleteAfterRun": j.delete_after_run,
                }
                for j in self._store.jobs
            ]
        }

        self.store_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self._last_mtime = self.store_path.stat().st_mtime

    async def start(self) -> None:
        """Start the cron service."""
        self._running = True
        self._load_store()
        self._recompute_next_runs()
        self._save_store()
        self._arm_timer()
        logger.info("Cron service started with {} jobs", len(self._store.jobs if self._store else []))

    def stop(self) -> None:
        """Stop the cron service."""
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

    def _recompute_next_runs(self) -> None:
        """Recompute next run times for all enabled jobs."""
        if not self._store:
            return
        now = _now_seconds()
        for job in self._store.jobs:
            if job.enabled:
                job.state.next_run_at_seconds = _compute_next_run(job.schedule, now)

    def _get_next_wake_seconds(self) -> int | None:
        """Get the earliest next run time across all jobs."""
        if not self._store:
            return None
        times = [j.state.next_run_at_seconds for j in self._store.jobs
                 if j.enabled and j.state.next_run_at_seconds]
        return min(times) if times else None

    def _arm_timer(self) -> None:
        """Schedule the next timer tick."""
        if self._timer_task:
            self._timer_task.cancel()

        next_wake = self._get_next_wake_seconds()
        if not next_wake or not self._running:
            return

        delay_seconds = max(0, next_wake - _now_seconds())

        async def tick():
            await asyncio.sleep(delay_seconds)
            if self._running:
                await self._on_timer()

        self._timer_task = asyncio.create_task(tick())

    async def _on_timer(self) -> None:
        """Handle timer tick - run due jobs."""
        self._load_store()
        if not self._store:
            return

        now = _now_seconds()
        due_jobs = [
            j for j in self._store.jobs
            if j.enabled and j.state.next_run_at_seconds and now >= j.state.next_run_at_seconds
        ]

        for job in due_jobs:
            await self._execute_job(job)

        self._save_store()
        self._arm_timer()

    async def _execute_job(self, job: CronJob) -> None:
        """Execute a single job."""
        start_seconds = _now_seconds()
        logger.info("Cron: executing job '{}' ({})", job.name, job.id)

        try:
            if self.on_job:
                await self.on_job(job)

            job.state.last_status = "ok"
            job.state.last_error = None
            logger.info("Cron: job '{}' completed", job.name)

        except Exception as e:
            job.state.last_status = "error"
            job.state.last_error = str(e)
            logger.error("Cron: job '{}' failed: {}", job.name, e)

        end_seconds = _now_seconds()
        job.state.last_run_at_seconds = start_seconds
        job.updated_at_seconds = end_seconds

        job.state.run_history.append(CronRunRecord(
            run_at_seconds=start_seconds,
            status=job.state.last_status,
            duration_seconds=end_seconds - start_seconds,
            error=job.state.last_error,
        ))
        job.state.run_history = job.state.run_history[-self._MAX_RUN_HISTORY:]

        # Handle one-shot jobs
        if job.schedule.kind == "at":
            if job.delete_after_run:
                self._store.jobs = [j for j in self._store.jobs if j.id != job.id]
            else:
                job.enabled = False
                job.state.next_run_at_seconds = None
        else:
            # Compute next run
            job.state.next_run_at_seconds = _compute_next_run(job.schedule, _now_seconds())

    # ========== Public API ==========

    def list_jobs(self, include_disabled: bool = False) -> list[CronJob]:
        """List all jobs."""
        store = self._load_store()
        jobs = store.jobs if include_disabled else [j for j in store.jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.state.next_run_at_seconds or float('inf'))

    def add_job(
        self,
        name: str,
        schedule: CronSchedule,
        message: str,
        deliver: bool = False,
        channel: str | None = None,
        to: str | None = None,
        delete_after_run: bool = False,
    ) -> CronJob:
        """Add a new job."""
        store = self._load_store()
        _validate_schedule_for_add(schedule)
        now = _now_seconds()

        job = CronJob(
            id=str(uuid.uuid4())[:8],
            name=name,
            enabled=True,
            schedule=schedule,
            payload=CronPayload(
                kind="agent_turn",
                message=message,
                deliver=deliver,
                channel=channel,
                to=to,
            ),
            state=CronJobState(next_run_at_seconds=_compute_next_run(schedule, now)),
            created_at_seconds=now,
            updated_at_seconds=now,
            delete_after_run=delete_after_run,
        )

        store.jobs.append(job)
        self._save_store()
        self._arm_timer()

        logger.info("Cron: added job '{}' ({})", name, job.id)
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a job by ID."""
        store = self._load_store()
        before = len(store.jobs)
        store.jobs = [j for j in store.jobs if j.id != job_id]
        removed = len(store.jobs) < before

        if removed:
            self._save_store()
            self._arm_timer()
            logger.info("Cron: removed job {}", job_id)

        return removed

    def enable_job(self, job_id: str, enabled: bool = True) -> CronJob | None:
        """Enable or disable a job."""
        store = self._load_store()
        for job in store.jobs:
            if job.id == job_id:
                job.enabled = enabled
                job.updated_at_seconds = _now_seconds()
                if enabled:
                    job.state.next_run_at_seconds = _compute_next_run(job.schedule, _now_seconds())
                else:
                    job.state.next_run_at_seconds = None
                self._save_store()
                self._arm_timer()
                return job
        return None

    async def run_job(self, job_id: str, force: bool = False) -> bool:
        """Manually run a job."""
        store = self._load_store()
        for job in store.jobs:
            if job.id == job_id:
                if not force and not job.enabled:
                    return False
                await self._execute_job(job)
                self._save_store()
                self._arm_timer()
                return True
        return False

    def get_job(self, job_id: str) -> CronJob | None:
        """Get a job by ID."""
        store = self._load_store()
        return next((j for j in store.jobs if j.id == job_id), None)

    def status(self) -> dict:
        """Get service status."""
        store = self._load_store()
        next_wake = self._get_next_wake_seconds()
        return {
            "enabled": self._running,
            "jobs": len(store.jobs),
            "next_wake_at_seconds": next_wake,
        }
