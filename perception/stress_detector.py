"""
Emotional / Stress Detection — monitors the user's interaction patterns
and system signals to detect stress or fatigue, then adapts agent behavior.

Detection signals:
1. Typing speed and error rate (via keyboard hook — pynput)
2. Mouse movement jitter / erratic movements
3. Task failure frequency (from performance metrics)
4. Time of day + work session duration
5. Repeated failed attempts at the same goal
6. Voice tone analysis (if microphone available — librosa)

Stress levels:
  0 = relaxed
  1 = focused
  2 = mildly stressed
  3 = stressed
  4 = frustrated / high stress
  5 = burnout — recommend break

When stress level >= 3, agent:
  - Slows down responses slightly (adds context before diving in)
  - Offers to break complex tasks into smaller steps
  - Proactively reports progress more often
  - At level 5: suggests taking a break

When stress level >= 4, agent:
  - Asks simpler clarifying questions
  - Prioritizes quick wins first
  - Avoids multi-step plans without confirmation
"""

from __future__ import annotations
import time
import threading
import math
from collections import deque
from dataclasses import dataclass
from typing import Optional, Callable
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class StressSignal:
    timestamp: float
    signal_type: str    # "typing_error" | "mouse_jitter" | "task_fail" | "retry" | "long_session"
    value: float        # normalized 0-1
    context: str = ""


@dataclass
class StressState:
    level: int              # 0-5
    label: str              # "relaxed" | "focused" | "mild" | "stressed" | "frustrated" | "burnout"
    confidence: float       # 0-1
    dominant_signal: str    # which signal is driving the score
    recommendations: list[str]
    should_suggest_break: bool

    def to_agent_context(self) -> str:
        if self.level <= 1:
            return ""  # no need to mention when user is fine
        parts = [f"[Stress Monitor] User stress level: {self.label} (level {self.level}/5)"]
        if self.recommendations:
            parts.append(f"Recommendations: {'; '.join(self.recommendations)}")
        if self.should_suggest_break:
            parts.append("Consider suggesting a short break.")
        return "\n".join(parts)


_LEVEL_LABELS = ["relaxed", "focused", "mild", "stressed", "frustrated", "burnout"]
_LEVEL_COLORS = ["#00cc00", "#88cc00", "#cccc00", "#cc8800", "#cc4400", "#cc0000"]


class StressDetector:
    """Monitor user stress and fatigue levels."""

    def __init__(
        self,
        window_seconds: int = 300,   # 5-min rolling window
        on_stress_change: Optional[Callable[[StressState], None]] = None,
    ):
        self._window = window_seconds
        self._on_change = on_stress_change
        self._signals: deque[StressSignal] = deque()
        self._lock = threading.Lock()
        self._session_start = time.time()
        self._current_level = 0
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

        # Keyboard monitoring state
        self._keystrokes: deque[float] = deque(maxlen=200)
        self._backspace_count = 0
        self._total_keys = 0

        # Mouse monitoring state
        self._mouse_positions: deque[tuple[float, float, float]] = deque(maxlen=100)  # (x, y, t)

        # Task failure tracking
        self._recent_fails = 0
        self._recent_retries = 0

    def start(self) -> None:
        """Start background stress monitoring."""
        self._monitoring = True
        self._start_keyboard_monitor()
        self._start_mouse_monitor()
        self._monitor_thread = threading.Thread(target=self._analysis_loop, daemon=True)
        self._monitor_thread.start()
        log.info("Stress detector started")

    def stop(self) -> None:
        self._monitoring = False

    # ── Event Recording (called by agent) ─────────────────────────────────────

    def record_task_fail(self) -> None:
        self._recent_fails += 1
        self._add_signal("task_fail", min(self._recent_fails / 5.0, 1.0))

    def record_retry(self) -> None:
        self._recent_retries += 1
        self._add_signal("retry", min(self._recent_retries / 3.0, 1.0))

    def record_task_success(self) -> None:
        """Reduce stress when tasks succeed."""
        self._recent_fails = max(0, self._recent_fails - 1)
        self._recent_retries = max(0, self._recent_retries - 1)

    # ── Stress Assessment ──────────────────────────────────────────────────────

    def get_current_state(self) -> StressState:
        """Return current stress state."""
        scores = self._compute_scores()
        level = self._compute_level(scores)
        dominant = max(scores, key=scores.get) if scores else "none"
        recommendations = self._get_recommendations(level, scores)
        session_hours = (time.time() - self._session_start) / 3600

        return StressState(
            level=level,
            label=_LEVEL_LABELS[level],
            confidence=self._compute_confidence(scores),
            dominant_signal=dominant,
            recommendations=recommendations,
            should_suggest_break=(level >= 4 or session_hours >= 4),
        )

    def _compute_scores(self) -> dict[str, float]:
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            recent = [s for s in self._signals if s.timestamp >= cutoff]

        scores: dict[str, float] = {}

        # Typing error rate
        typing_errors = [s for s in recent if s.signal_type == "typing_error"]
        if typing_errors:
            scores["typing_errors"] = min(sum(s.value for s in typing_errors) / 10.0, 1.0)

        # Mouse jitter
        jitter_signals = [s for s in recent if s.signal_type == "mouse_jitter"]
        if jitter_signals:
            scores["mouse_jitter"] = min(sum(s.value for s in jitter_signals) / 5.0, 1.0)

        # Task failures
        fail_signals = [s for s in recent if s.signal_type == "task_fail"]
        if fail_signals:
            scores["task_failures"] = min(len(fail_signals) / 3.0, 1.0)

        # Retry patterns
        retry_signals = [s for s in recent if s.signal_type == "retry"]
        if retry_signals:
            scores["retries"] = min(len(retry_signals) / 5.0, 1.0)

        # Long session (fatigue)
        session_hours = (time.time() - self._session_start) / 3600
        if session_hours > 2:
            scores["long_session"] = min((session_hours - 2) / 4.0, 1.0)

        # Time of day (late night = stress signal)
        import datetime
        hour = datetime.datetime.now().hour
        if hour >= 23 or hour <= 5:
            scores["late_night"] = 0.4

        return scores

    def _compute_level(self, scores: dict[str, float]) -> int:
        if not scores:
            return 0
        avg = sum(scores.values()) / len(scores)
        max_score = max(scores.values())
        combined = avg * 0.4 + max_score * 0.6
        return min(int(combined * 5.5), 5)

    def _compute_confidence(self, scores: dict[str, float]) -> float:
        """Higher confidence with more signals."""
        return min(len(scores) / 4.0, 1.0)

    def _get_recommendations(self, level: int, scores: dict[str, float]) -> list[str]:
        recs = []
        if level >= 2 and scores.get("typing_errors", 0) > 0.4:
            recs.append("Slow down — many typing errors detected")
        if level >= 3 and scores.get("task_failures", 0) > 0.3:
            recs.append("Break complex task into smaller steps")
        if level >= 4:
            recs.append("Consider taking a 5-10 minute break")
        if level >= 3 and scores.get("long_session", 0) > 0.3:
            recs.append("You've been working for several hours — hydrate and stretch")
        if level == 5:
            recs.append("High fatigue detected — rest is essential for clear thinking")
        return recs

    # ── Background Analysis ────────────────────────────────────────────────────

    def _analysis_loop(self) -> None:
        prev_level = 0
        while self._monitoring:
            time.sleep(30)  # assess every 30 seconds
            state = self.get_current_state()
            if state.level != prev_level:
                prev_level = state.level
                if state.level > 0:
                    log.info(f"Stress level changed to: {state.label} (level {state.level})")
                if self._on_change:
                    self._on_change(state)

    def _add_signal(self, signal_type: str, value: float, context: str = "") -> None:
        with self._lock:
            self._signals.append(StressSignal(
                timestamp=time.time(),
                signal_type=signal_type,
                value=value,
                context=context,
            ))
            # Trim old signals
            cutoff = time.time() - self._window
            while self._signals and self._signals[0].timestamp < cutoff:
                self._signals.popleft()

    # ── Keyboard Monitoring ────────────────────────────────────────────────────

    def _start_keyboard_monitor(self) -> None:
        try:
            from pynput import keyboard

            def on_press(key):
                now = time.time()
                self._keystrokes.append(now)
                self._total_keys += 1
                if key == keyboard.Key.backspace:
                    self._backspace_count += 1
                    # High backspace ratio = errors = stress
                    if self._total_keys > 20:
                        error_rate = self._backspace_count / self._total_keys
                        if error_rate > 0.15:
                            self._add_signal("typing_error", min(error_rate * 3, 1.0))
                            self._backspace_count = 0
                            self._total_keys = 0

            listener = keyboard.Listener(on_press=on_press, suppress=False)
            listener.daemon = True
            listener.start()
        except ImportError:
            log.debug("pynput not available — keyboard stress monitoring disabled")
        except Exception as e:
            log.debug(f"Keyboard monitor failed: {e}")

    # ── Mouse Monitoring ───────────────────────────────────────────────────────

    def _start_mouse_monitor(self) -> None:
        try:
            from pynput import mouse

            def on_move(x, y):
                now = time.time()
                self._mouse_positions.append((x, y, now))
                if len(self._mouse_positions) >= 10:
                    jitter = self._compute_mouse_jitter()
                    if jitter > 0.5:
                        self._add_signal("mouse_jitter", jitter)

            listener = mouse.Listener(on_move=on_move)
            listener.daemon = True
            listener.start()
        except ImportError:
            log.debug("pynput not available — mouse stress monitoring disabled")
        except Exception as e:
            log.debug(f"Mouse monitor failed: {e}")

    def _compute_mouse_jitter(self) -> float:
        """Compute erratic mouse movement score (0-1)."""
        positions = list(self._mouse_positions)
        if len(positions) < 5:
            return 0.0

        # Compute direction changes (frequent direction reversals = jitter)
        direction_changes = 0
        for i in range(2, len(positions)):
            x0, y0, _ = positions[i-2]
            x1, y1, _ = positions[i-1]
            x2, y2, _ = positions[i]
            dx1, dy1 = x1 - x0, y1 - y0
            dx2, dy2 = x2 - x1, y2 - y1
            # Dot product — negative means direction reversal
            dot = dx1 * dx2 + dy1 * dy2
            if dot < -100:  # significant reversal
                direction_changes += 1

        jitter_rate = direction_changes / len(positions)
        return min(jitter_rate * 5, 1.0)

    def get_stress_report(self) -> str:
        """Human-readable stress report."""
        state = self.get_current_state()
        session_min = int((time.time() - self._session_start) / 60)
        lines = [
            f"Stress Level: {state.label.upper()} ({state.level}/5)",
            f"Session Duration: {session_min} minutes",
            f"Dominant Signal: {state.dominant_signal}",
            f"Confidence: {state.confidence:.0%}",
        ]
        if state.recommendations:
            lines.append(f"Recommendations: {'; '.join(state.recommendations)}")
        return "\n".join(lines)
