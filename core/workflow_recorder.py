"""
WorkflowRecorder — records every action the agent (or human) takes,
then converts the sequence into a named reusable tool.

Two modes:
  1. Agent recording: automatically records agent's own actions
  2. Human recording: hooks into mouse/keyboard to record human demos

When you say "record this as a workflow named X", the recorder
saves the sequence and the agent can replay it later with one call.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable
from utils.logger import get_logger

log = get_logger(__name__)

_WORKFLOWS_DIR = Path("data/workflows")


@dataclass
class RecordedStep:
    action: str
    args: dict
    timestamp: float = field(default_factory=time.time)
    screenshot_before: str = ""  # path to screenshot
    result: str = ""


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: list[RecordedStep]
    created: float = field(default_factory=time.time)
    run_count: int = 0
    tags: list[str] = field(default_factory=list)


class WorkflowRecorder:

    def __init__(self):
        _WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
        self._recording = False
        self._current_steps: list[RecordedStep] = []
        self._current_name = ""

    def start_recording(self, name: str = "") -> None:
        self._recording = True
        self._current_steps = []
        self._current_name = name or f"workflow_{int(time.time())}"
        log.info(f"Recording started: {self._current_name}")

    def stop_recording(self, name: str = "", description: str = "") -> Workflow | None:
        if not self._recording or not self._current_steps:
            self._recording = False
            return None
        self._recording = False
        wf_name = name or self._current_name
        wf = Workflow(
            id=str(uuid.uuid4())[:8],
            name=wf_name,
            description=description or f"Recorded workflow: {wf_name}",
            steps=self._current_steps.copy(),
        )
        self._save(wf)
        log.info(f"Workflow saved: '{wf_name}' ({len(wf.steps)} steps)")
        return wf

    def record_step(self, action: str, args: dict, result: str = "") -> None:
        if not self._recording:
            return
        step = RecordedStep(action=action, args=args, result=result)
        self._current_steps.append(step)

    def is_recording(self) -> bool:
        return self._recording

    def list_workflows(self) -> list[dict]:
        workflows = []
        for f in _WORKFLOWS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                workflows.append({
                    "id": data["id"],
                    "name": data["name"],
                    "description": data["description"],
                    "steps": len(data["steps"]),
                    "run_count": data.get("run_count", 0),
                })
            except Exception:
                pass
        return workflows

    def load(self, name_or_id: str) -> Workflow | None:
        for f in _WORKFLOWS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data["name"] == name_or_id or data["id"] == name_or_id:
                    steps = [RecordedStep(**s) for s in data["steps"]]
                    return Workflow(**{**data, "steps": steps})
            except Exception:
                pass
        return None

    def get_replay_plan(self, workflow: Workflow) -> str:
        """Returns a text description of the workflow steps for the agent."""
        lines = [f"Workflow: {workflow.name}"]
        for i, step in enumerate(workflow.steps, 1):
            lines.append(f"  {i}. {step.action}({step.args})")
        return "\n".join(lines)

    def _save(self, workflow: Workflow) -> None:
        data = asdict(workflow)
        path = _WORKFLOWS_DIR / f"{workflow.id}_{workflow.name}.json"
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def delete(self, name_or_id: str) -> bool:
        for f in _WORKFLOWS_DIR.glob("*.json"):
            try:
                data = json.loads(f.read_text())
                if data["name"] == name_or_id or data["id"] == name_or_id:
                    f.unlink()
                    return True
            except Exception:
                pass
        return False
