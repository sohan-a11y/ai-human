"""
ProactiveMonitor — the agent watches the screen passively even without a goal.
When it detects something notable (error, alert, notification, low resources),
it either alerts the user or handles it automatically.

This transforms the agent from a "when asked" tool into a real coworker
that notices things on its own.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from perception.screen_capture import ScreenCapture
from perception.screen_diff import ScreenDiff
from llm.base import LLMProvider
from llm.message_builder import system_message, vision_message
from core.event_bus import EventBus
from utils.logger import get_logger

log = get_logger(__name__)

_WATCH_PROMPT = """Look at this screenshot. Identify if there is anything that requires attention:
- Error dialogs or warning popups
- System notifications
- Low battery / disk / memory warnings
- Completed downloads or installs
- Login prompts
- Application crashes
- Any urgent message

Return JSON:
{
  "alert": true/false,
  "severity": "low|medium|high",
  "description": "what you see that needs attention",
  "suggested_action": "what the agent should do, or empty string if just notify"
}
Return only JSON."""


@dataclass
class ProactiveAlert:
    severity: str
    description: str
    suggested_action: str
    screenshot_path: str = ""


class ProactiveMonitor:

    def __init__(
        self,
        llm: LLMProvider,
        event_bus: EventBus,
        goal_callback,
        check_interval: float = 30.0,
        min_change_to_analyze: float = 2.0,
    ):
        self._llm = llm
        self._bus = event_bus
        self._goal_callback = goal_callback
        self._interval = check_interval
        self._min_change = min_change_to_analyze
        self._running = False
        self._thread: threading.Thread | None = None
        self._capture = ScreenCapture()
        self._diff = ScreenDiff()
        self._last_screenshot = None
        self._auto_handle_high = True   # auto-handle high severity alerts

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ProactiveMonitor")
        self._thread.start()
        log.info("Proactive monitor started")

    def stop(self) -> None:
        self._running = False

    def _loop(self) -> None:
        while self._running:
            try:
                self._check()
            except Exception as e:
                log.debug(f"Proactive monitor error: {e}")
            time.sleep(self._interval)

    def _check(self) -> None:
        current = self._capture.capture()

        # Skip if screen hasn't changed much (saves LLM calls)
        if self._last_screenshot is not None:
            diff = self._diff.compare(self._last_screenshot, current)
            if not diff.changed or diff.change_percent < self._min_change:
                self._last_screenshot = current
                return

        self._last_screenshot = current

        # Only analyze if vision LLM available
        if not self._llm.supports_vision():
            return

        alert = self._analyze(current)
        if not alert:
            return

        log.info(f"Proactive alert [{alert.severity}]: {alert.description}")
        self._bus.publish("proactive_alert", {
            "severity": alert.severity,
            "description": alert.description,
            "action": alert.suggested_action,
        })

        # Auto-handle high severity (e.g. error dialog)
        if self._auto_handle_high and alert.severity == "high" and alert.suggested_action:
            log.info(f"Auto-handling high severity: {alert.suggested_action}")
            self._goal_callback(alert.suggested_action)

    def _analyze(self, img) -> ProactiveAlert | None:
        try:
            import json
            messages = [
                system_message("You detect important screen events. Return only JSON."),
                vision_message("user", _WATCH_PROMPT, [img]),
            ]
            raw = self._llm.generate(messages)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)
            if not data.get("alert"):
                return None
            return ProactiveAlert(
                severity=data.get("severity", "low"),
                description=data.get("description", ""),
                suggested_action=data.get("suggested_action", ""),
            )
        except Exception as e:
            log.debug(f"Proactive analysis failed: {e}")
            return None
