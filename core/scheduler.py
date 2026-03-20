"""
Scheduler — runs agent goals on a time-based schedule.
Supports: one-time, recurring (cron-style), interval, and daily schedules.
Persists schedules to disk so they survive restarts.

Examples:
  scheduler.add("every_day", "08:00", "Check email and summarize")
  scheduler.add("every_hour", None, "Check if builds are passing")
  scheduler.add("interval", 1800, "Monitor disk usage")     # every 30 min
  scheduler.add("once", "2026-03-15 09:00", "Submit report")
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable
from utils.logger import get_logger

log = get_logger(__name__)

_SCHEDULE_FILE = Path("data/schedules.json")


@dataclass
class ScheduledTask:
    id: str
    schedule_type: str   # every_day | every_hour | interval | once | cron
    schedule_value: str  # "08:00" / seconds / "2026-03-15 09:00" / cron expr
    goal: str
    enabled: bool = True
    last_run: float = 0.0
    run_count: int = 0
    created: float = field(default_factory=time.time)


class Scheduler:

    def __init__(self, goal_callback: Callable[[str], None]):
        """goal_callback: called with goal string when a task fires."""
        self._callback = goal_callback
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        _SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def add(self, schedule_type: str, schedule_value, goal: str) -> str:
        """Add a scheduled task. Returns task ID."""
        task = ScheduledTask(
            id=str(uuid.uuid4())[:8],
            schedule_type=schedule_type,
            schedule_value=str(schedule_value),
            goal=goal,
        )
        self._tasks[task.id] = task
        self._save()
        log.info(f"Scheduled: [{task.id}] '{goal[:50]}' — {schedule_type} {schedule_value}")
        return task.id

    def remove(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save()
            return True
        return False

    def list_tasks(self) -> list[dict]:
        return [asdict(t) for t in self._tasks.values()]

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="Scheduler")
        self._thread.start()
        log.info("Scheduler started")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            now = time.time()
            for task in list(self._tasks.values()):
                if task.enabled and self._should_run(task, now):
                    log.info(f"Scheduler firing: [{task.id}] {task.goal[:50]}")
                    task.last_run = now
                    task.run_count += 1
                    self._save()
                    try:
                        self._callback(task.goal)
                    except Exception as e:
                        log.error(f"Scheduled task error: {e}")
            time.sleep(30)  # check every 30 seconds

    def _should_run(self, task: ScheduledTask, now: float) -> bool:
        t = task.schedule_type
        v = task.schedule_value

        if t == "interval":
            interval = float(v)
            return (now - task.last_run) >= interval

        elif t == "every_hour":
            return (now - task.last_run) >= 3600

        elif t == "every_day":
            # v is "HH:MM"
            import datetime
            target = datetime.datetime.now().replace(
                hour=int(v.split(":")[0]),
                minute=int(v.split(":")[1]),
                second=0, microsecond=0
            )
            target_ts = target.timestamp()
            # Fire if we're within 60s of target and haven't run in last 23h
            return (abs(now - target_ts) < 60) and (now - task.last_run > 82800)

        elif t == "once":
            import datetime
            try:
                target_ts = datetime.datetime.strptime(v, "%Y-%m-%d %H:%M").timestamp()
                return (now >= target_ts) and (task.run_count == 0)
            except Exception:
                return False

        elif t == "cron":
            try:
                from croniter import croniter
                cr = croniter(v, task.last_run or now - 120)
                next_run = cr.get_next(float)
                return now >= next_run
            except ImportError:
                log.warning("croniter not installed for cron schedules: pip install croniter")
                return False

        return False

    def _save(self) -> None:
        data = {tid: asdict(t) for tid, t in self._tasks.items()}
        _SCHEDULE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not _SCHEDULE_FILE.exists():
            return
        try:
            data = json.loads(_SCHEDULE_FILE.read_text())
            for tid, t in data.items():
                self._tasks[tid] = ScheduledTask(**t)
            log.info(f"Loaded {len(self._tasks)} scheduled tasks")
        except Exception as e:
            log.warning(f"Could not load schedules: {e}")
