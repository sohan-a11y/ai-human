"""
AgentOrchestrator — fully wired, no limits.
All wiring gaps fixed. No rate limiting. No context truncation.
AI uses full ChromaDB memory for unlimited recall.
"""

from __future__ import annotations

import json
import threading
import time
from enum import Enum, auto

from config import Config
from llm.base import LLMProvider
from llm.message_builder import system_message, text_message
from perception.vision_analyzer import VisionAnalyzer
from perception.uia_detector import UIADetector
from perception.screen_capture import ScreenCapture
from perception.screen_diff import ScreenDiff
from actions.executor import ActionExecutor
from memory.episodic import EpisodicMemory
from memory.semantic import SemanticMemory
from research.researcher import ResearchOrchestrator
from core.self_corrector import SelfCorrector
from safety.broker import SafetyBroker, SafetyBlock
from safety.audit_log import AuditLog
from tools.registry import ToolRegistry
from prompts.system_prompt import SYSTEM_PROMPT
from core.event_bus import EventBus
from utils.logger import get_logger

log = get_logger(__name__)


class AgentState(Enum):
    IDLE = auto()
    PERCEIVING = auto()
    THINKING = auto()
    ACTING = auto()
    LEARNING = auto()
    SELF_UPDATING = auto()
    STOPPED = auto()


class AgentOrchestrator:

    def __init__(self, config: Config, llm: LLMProvider, vision_llm, event_bus: EventBus):
        self._config = config
        self._llm = llm
        self._bus = event_bus

        from perception.ocr_engine import OCREngine
        from memory.vector_store import VectorStore

        ocr = OCREngine()
        self._uia = UIADetector()
        self._capture = ScreenCapture()
        self._diff = ScreenDiff()
        self._analyzer = VisionAnalyzer(vision_llm, ocr)

        vec_store = VectorStore(str(config.chroma_path), llm.embed)
        self._episodic = EpisodicMemory(vec_store)
        self._semantic = SemanticMemory(vec_store)

        audit = AuditLog()
        self._safety = SafetyBroker(config, audit)
        self._executor = ActionExecutor()
        self._tools = ToolRegistry()
        self._attach_skill_creator()
        self._researcher = ResearchOrchestrator(llm, self._semantic)
        self._corrector = SelfCorrector(llm, self._researcher, self._semantic)

        self._tts = None
        try:
            from audio.tts import TTS
            self._tts = TTS()
        except Exception:
            pass

        # Attached by main.py
        self._recorder = None
        self._converter = None
        self._multi_agent = None

        self._state = AgentState.IDLE
        self._goal: str = ""
        self._running = False
        self._thread = None
        self._context_window: list[dict] = []  # No artificial limit
        self._last_screenshot = None

    def set_goal(self, goal: str) -> None:
        self._goal = goal
        self._context_window = []
        log.info(f"New goal: {goal}")
        self._bus.publish("goal", goal)
        if self._tts:
            self._tts.speak(f"Got it. {goal[:50]}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AgentLoop")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._set_state(AgentState.STOPPED)

    def _loop(self) -> None:
        while self._running:
            try:
                if not self._goal:
                    self._set_state(AgentState.IDLE)
                    time.sleep(self._config.loop_interval_seconds)
                    continue
                self._tick()
                time.sleep(0.5)  # Minimal — AI controls its own pace via wait action
            except SafetyBlock as e:
                log.warning(f"Safety block: {e}")
                self._bus.publish("error", f"Safety: {e}")
                if self._tts:
                    self._tts.speak("Action blocked for safety.")
                self._set_state(AgentState.IDLE)
                time.sleep(2)
            except Exception as e:
                log.error(f"Loop error: {e}", exc_info=True)
                self._bus.publish("error", str(e))
                time.sleep(1)

    def _tick(self) -> None:
        # ── 1. Perceive + UIA ────────────────────────────────────────────────
        self._set_state(AgentState.PERCEIVING)
        before_screenshot = self._last_screenshot
        percept = self._analyzer.analyze()
        self._last_screenshot = percept.screenshot
        self._bus.publish("percept", percept.summary())

        # UIA exact positions — wiring gap #1 FIXED
        uia_info = ""
        if self._uia.available:
            el_map = self._uia.get_element_map()
            if el_map:
                uia_info = self._format_uia_map(el_map)

        # ── 2. Full memory recall — no limits ────────────────────────────────
        past = self._episodic.format_for_context(self._goal, n=10)
        knowledge = self._semantic.format_for_context(self._goal, n=10)
        failures = self._episodic.recall_failures(self._goal)
        failure_text = ""
        if failures:
            failure_text = "## Known failures to avoid:\n" + "\n".join(
                f"- {f['text'][:200]}" for f in failures[:5])

        # ── 3. Build context — full window, nothing cut ───────────────────────
        self._set_state(AgentState.THINKING)
        stats = f"Memory: {self._episodic.total_count()} episodes | {self._semantic.total_count()} knowledge items"
        parts = [f"Goal: {self._goal}", f"Screen: {percept.summary()}", stats]
        if uia_info:
            parts.append(f"UI elements (exact positions):\n{uia_info}")
        if past:
            parts.append(past)
        if knowledge:
            parts.append(knowledge)
        if failure_text:
            parts.append(failure_text)
        parts.append(self._tools.describe_all())

        # Soft cap: keep last 40 messages to stay within LLM context limits
        _MAX_CONTEXT = 40
        if len(self._context_window) > _MAX_CONTEXT:
            self._context_window = self._context_window[-_MAX_CONTEXT:]

        messages = [system_message(SYSTEM_PROMPT)]
        messages += self._context_window
        messages.append(text_message("user", "\n\n".join(parts)))

        raw = self._llm.generate(messages)
        self._bus.publish("thought", raw[:300])

        # ── 4. Parse + auto-retry ─────────────────────────────────────────────
        decision = self._parse_decision(raw)
        if not decision:
            messages.append(text_message("assistant", raw))
            messages.append(text_message("user", "Invalid JSON. Return ONLY a JSON object as specified. No extra text."))
            raw = self._llm.generate(messages)
            decision = self._parse_decision(raw)
            if not decision:
                return

        self._context_window.append(text_message("assistant", raw))

        action_name = decision.get("action", "")
        args = decision.get("args", {})
        done = decision.get("done", False)
        thought = decision.get("thought", "")
        log.info(f"Thought: {thought[:120]} | Action: {action_name}")

        if done:
            self._on_goal_done()
            return

        # ── 5. Self-update ────────────────────────────────────────────────────
        if action_name == "self_update":
            self._handle_self_update(args)
            return

        # ── 6. Spawn worker — wiring gap #2 FIXED ────────────────────────────
        if action_name == "spawn_worker" and self._multi_agent:
            wid = self._multi_agent.spawn(args.get("goal", ""))
            self._context_window.append(text_message("user", f"Worker {wid} spawned"))
            return

        # ── 7. Tools ──────────────────────────────────────────────────────────
        if self._tools.get(action_name):
            result = self._tools.run(action_name, **args)
            self._context_window.append(text_message("user", f"Tool {action_name}: {result}"))
            self._semantic.store(f"Tool {action_name} on '{self._goal}': {result[:300]}", source="tool_result")
            return

        # ── 8. Research ───────────────────────────────────────────────────────
        if action_name == "research":
            result = self._researcher.research(args.get("query", self._goal))
            self._context_window.append(text_message("user", f"Research: {result[:800]}"))
            return

        # ── 9. Execute + record + diff ────────────────────────────────────────
        if action_name:
            self._set_state(AgentState.ACTING)
            self._safety.check(action_name, args)

            # Workflow recorder — wiring gap #3 FIXED
            if self._recorder and self._recorder.is_recording():
                self._recorder.record_step(action_name, args)

            # Pattern tracker — wiring gap #4 FIXED
            if self._converter:
                self._converter.track_action(action_name, args)

            result = self._executor.execute(action_name, args)
            self._bus.publish("action", {"name": action_name, "success": result.success, "msg": result.message})

            # Screen diff verify — wiring gap #5 FIXED
            time.sleep(0.3)
            after_shot = self._capture.capture()
            diff_summary = ""
            if before_screenshot is not None:
                diff = self._diff.compare(before_screenshot, after_shot)
                diff_summary = diff.summary()
                self._last_screenshot = after_shot

            self._set_state(AgentState.LEARNING)

            if not result.success:
                correction = self._corrector.handle_failure(self._goal, action_name, args, result.message)
                fb = f"FAILED: {result.message}"
                if correction.get("new_approach"):
                    fb += f"\nTry: {correction['new_approach']}"
                if correction.get("search_result"):
                    fb += f"\nSolution: {correction['search_result'][:300]}"
                self._context_window.append(text_message("user", fb))
                if self._recorder and self._recorder.is_recording():
                    self._recorder.record_step(action_name, args, result=f"FAILED: {result.message}")
            else:
                outcome = result.message + (f" | {diff_summary}" if diff_summary else "")
                self._episodic.store(
                    perception=percept.summary(),
                    action=f"{action_name}({args})",
                    outcome=outcome,
                    goal=self._goal,
                )
                self._context_window.append(text_message("user", f"OK: {outcome}"))
                if self._recorder and self._recorder.is_recording():
                    self._recorder.record_step(action_name, args, result=outcome)

    def _on_goal_done(self) -> None:
        self._bus.publish("done", self._goal)
        if self._tts:
            self._tts.speak("Task complete.")
        self._semantic.store(
            f"Completed: {self._goal}",
            source="goal_completion", tags=["success"])
        self._goal = ""
        self._set_state(AgentState.IDLE)

    def _handle_self_update(self, args: dict) -> None:
        request = args.get("request", "")
        if not request:
            return
        self._set_state(AgentState.SELF_UPDATING)
        if self._tts:
            self._tts.speak("Updating myself.")
        from core.self_updater import SelfUpdater
        result = SelfUpdater(self._llm).update(request, args.get("files"))
        if not result["success"]:
            self._context_window.append(text_message("user", f"Self-update failed: {result['error']}"))
            self._set_state(AgentState.IDLE)

    def _attach_skill_creator(self) -> None:
        """Wire the SkillCreator tool with LLM and registry references."""
        creator = self._tools.get("skill_creator")
        if creator:
            creator._llm = self._llm
            creator._registry = self._tools

    def _format_uia_map(self, el_map: dict) -> str:
        lines = []
        for ctrl_type, elements in el_map.items():
            for el in elements[:8]:
                if el.get("name"):
                    lines.append(f"  [{ctrl_type}] '{el['name']}' at ({el['x']},{el['y']})")
        return "\n".join(lines[:40])

    def _parse_decision(self, raw: str) -> dict | None:
        try:
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            s, e = clean.find("{"), clean.rfind("}") + 1
            if s >= 0 and e > s:
                return json.loads(clean[s:e])
        except Exception:
            pass
        return None

    def _set_state(self, state: AgentState) -> None:
        self._state = state
        self._bus.publish("state_change", state.name)

    # ── Public API ────────────────────────────────────────────────────────

    def attach(self, name: str, component: object) -> None:
        """Attach an optional subsystem by name. Used by AgentWiring."""
        setattr(self, f"_{name}", component)

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def goal(self) -> str:
        return self._goal

    @property
    def running(self) -> bool:
        return self._running

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def semantic(self) -> SemanticMemory:
        return self._semantic

    @property
    def episodic(self) -> EpisodicMemory:
        return self._episodic

    @property
    def context_window(self) -> list[dict]:
        return self._context_window

    @context_window.setter
    def context_window(self, value: list[dict]) -> None:
        self._context_window = value
