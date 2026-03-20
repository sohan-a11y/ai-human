"""
MultiAgentManager — spawn and coordinate multiple AI worker instances.
Workers run in parallel threads, each with their own goal and context.
They share the same vector memory pool so learned knowledge is shared.

Use cases:
  - "Research X while I execute Y"
  - "Monitor email + work on task simultaneously"
  - "Split a large task into parallel subtasks"
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from llm.base import LLMProvider
from core.event_bus import EventBus
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class WorkerStatus:
    worker_id: str
    goal: str
    state: str = "IDLE"
    started: float = field(default_factory=time.time)
    completed: bool = False
    result: str = ""
    error: str = ""


class AgentWorker:
    """A lightweight agent worker that runs a single goal and reports back."""

    def __init__(self, worker_id: str, llm: LLMProvider, vision_llm, config, shared_bus: EventBus):
        self._id = worker_id
        self._status = WorkerStatus(worker_id=worker_id, goal="")
        self._thread: threading.Thread | None = None

        # Each worker gets its own mini event bus
        self._local_bus = EventBus()

        # Import here to avoid circular imports
        from config import Config
        from memory.vector_store import VectorStore
        from memory.episodic import EpisodicMemory
        from memory.semantic import SemanticMemory
        from research.researcher import ResearchOrchestrator
        from actions.executor import ActionExecutor
        from safety.broker import SafetyBroker
        from safety.audit_log import AuditLog
        from tools.registry import ToolRegistry

        vec_store = VectorStore(str(config.chroma_path), llm.embed)
        self._episodic = EpisodicMemory(vec_store)
        self._semantic = SemanticMemory(vec_store)
        self._researcher = ResearchOrchestrator(llm, self._semantic)
        self._executor = ActionExecutor()
        self._tools = ToolRegistry()
        self._llm = llm
        self._config = config
        self._shared_bus = shared_bus
        self._context: list[dict] = []

    def run_goal(self, goal: str, on_complete: Callable | None = None) -> None:
        self._status.goal = goal
        self._status.state = "RUNNING"
        self._thread = threading.Thread(
            target=self._execute,
            args=(goal, on_complete),
            daemon=True,
            name=f"Worker-{self._id[:6]}",
        )
        self._thread.start()

    def _execute(self, goal: str, on_complete: Callable | None) -> None:
        from llm.message_builder import system_message, text_message
        from prompts.system_prompt import SYSTEM_PROMPT
        import json

        log.info(f"Worker {self._id[:6]} starting: {goal}")
        max_steps = 20

        for step in range(max_steps):
            try:
                # Build context
                knowledge = self._semantic.format_for_context(goal)
                tools_desc = self._tools.describe_all()

                parts = [f"Goal: {goal}"]
                if knowledge:
                    parts.append(knowledge)
                parts.append(tools_desc)
                parts.append("Note: You are a background worker. Focus on gathering information and completing the goal. Do NOT take UI actions unless explicitly required.")

                messages = [system_message(SYSTEM_PROMPT)]
                messages += self._context[-4:]
                messages.append(text_message("user", "\n\n".join(parts)))

                raw = self._llm.generate(messages)
                self._context.append(text_message("assistant", raw))

                # Parse
                clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
                start, end = clean.find("{"), clean.rfind("}") + 1
                decision = json.loads(clean[start:end]) if start >= 0 and end > start else {}

                action = decision.get("action", "")
                args = decision.get("args", {})
                done = decision.get("done", False)

                if done:
                    result = decision.get("thought", "Goal completed")
                    self._status.result = result
                    self._status.completed = True
                    self._status.state = "DONE"
                    log.info(f"Worker {self._id[:6]} done: {result[:80]}")
                    self._shared_bus.publish("worker_done", {"id": self._id, "goal": goal, "result": result})
                    if on_complete:
                        on_complete(self._id, result)
                    return

                # Handle tools
                if self._tools.get(action):
                    result = self._tools.run(action, **args)
                    self._context.append(text_message("user", f"Tool result: {result[:500]}"))
                elif action == "research":
                    result = self._researcher.research(args.get("query", goal))
                    self._context.append(text_message("user", f"Research: {result[:500]}"))

                time.sleep(0.5)

            except Exception as e:
                log.error(f"Worker {self._id[:6]} error: {e}")
                self._status.error = str(e)
                self._status.state = "ERROR"
                return

        self._status.state = "TIMEOUT"
        self._status.result = "Reached max steps without completing goal"

    @property
    def status(self) -> WorkerStatus:
        return self._status


class MultiAgentManager:

    def __init__(self, llm: LLMProvider, vision_llm, config, event_bus: EventBus):
        self._llm = llm
        self._vision_llm = vision_llm
        self._config = config
        self._bus = event_bus
        self._workers: dict[str, AgentWorker] = {}

    def spawn(self, goal: str, on_complete: Callable | None = None) -> str:
        """Spawn a worker for the given goal. Returns worker_id."""
        worker_id = str(uuid.uuid4())[:8]
        worker = AgentWorker(worker_id, self._llm, self._vision_llm, self._config, self._bus)
        self._workers[worker_id] = worker
        worker.run_goal(goal, on_complete)
        log.info(f"Spawned worker {worker_id}: {goal[:60]}")
        self._bus.publish("worker_spawned", {"id": worker_id, "goal": goal})
        return worker_id

    def spawn_parallel(self, goals: list[str]) -> list[str]:
        """Spawn multiple workers in parallel. Returns list of worker IDs."""
        return [self.spawn(goal) for goal in goals]

    def get_status(self, worker_id: str) -> WorkerStatus | None:
        w = self._workers.get(worker_id)
        return w.status if w else None

    def get_all_statuses(self) -> list[dict]:
        return [
            {
                "id": wid,
                "goal": w.status.goal[:60],
                "state": w.status.state,
                "result": w.status.result[:100],
            }
            for wid, w in self._workers.items()
        ]

    def wait_all(self, timeout: float = 120.0) -> list[WorkerStatus]:
        """Wait for all active workers to finish. Returns their statuses."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            active = [w for w in self._workers.values()
                      if w.status.state in ("RUNNING", "IDLE")]
            if not active:
                break
            time.sleep(1)
        return [w.status for w in self._workers.values()]

    def cleanup(self) -> None:
        """Remove completed workers."""
        done = [wid for wid, w in self._workers.items()
                if w.status.state in ("DONE", "ERROR", "TIMEOUT")]
        for wid in done:
            del self._workers[wid]
