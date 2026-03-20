"""
GoalPersistence — saves active goals, context, and progress to disk.
If the agent restarts (crash, self-update, reboot), it resumes where it left off.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from utils.logger import get_logger

log = get_logger(__name__)

_GOALS_FILE = Path("data/goals.json")


class GoalPersistence:

    def __init__(self):
        _GOALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    def save(self, goal: str, context_window: list[dict], metadata: dict | None = None) -> None:
        """Save current goal and conversation context to disk."""
        if not goal:
            self.clear()
            return
        data = {
            "goal": goal,
            "saved_at": time.time(),
            "saved_at_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "context_window": context_window[-10:],  # last 10 messages only
            "metadata": metadata or {},
        }
        _GOALS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        log.debug(f"Goal saved: {goal[:60]}")

    def load(self) -> dict | None:
        """Load persisted goal. Returns None if none saved or too old (>24h)."""
        if not _GOALS_FILE.exists():
            return None
        try:
            data = json.loads(_GOALS_FILE.read_text())
            age_hours = (time.time() - data.get("saved_at", 0)) / 3600
            if age_hours > 24:
                log.info("Persisted goal is older than 24h — discarding")
                self.clear()
                return None
            log.info(f"Restored goal: {data['goal'][:60]} (saved {age_hours:.1f}h ago)")
            return data
        except Exception as e:
            log.warning(f"Could not load persisted goal: {e}")
            return None

    def clear(self) -> None:
        if _GOALS_FILE.exists():
            _GOALS_FILE.unlink()

    def has_saved_goal(self) -> bool:
        return _GOALS_FILE.exists()
