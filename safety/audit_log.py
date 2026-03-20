"""Append-only JSONL audit trail of every action the agent attempts."""

from __future__ import annotations

import json
import time
from pathlib import Path


class AuditLog:

    def __init__(self, path: str = "data/audit/audit.jsonl"):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, action_name: str, args: dict, risk_score: int, reason: str, outcome: str = "pending") -> None:
        entry = {
            "ts": time.time(),
            "action": action_name,
            "args": args,
            "risk_score": risk_score,
            "reason": reason,
            "outcome": outcome,
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def update_outcome(self, action_name: str, success: bool, message: str) -> None:
        self.log(action_name, {}, 0, "", outcome="success" if success else f"failed: {message}")
