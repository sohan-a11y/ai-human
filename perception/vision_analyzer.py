"""
VisionAnalyzer: sends a screenshot to the vision-capable LLM and gets back
a structured description of what is on screen.

Falls back to OCR text if no vision model is available.
"""

from __future__ import annotations

import time
from PIL import Image

from llm.base import LLMProvider
from llm.message_builder import vision_message, text_message, system_message
from perception.ocr_engine import OCREngine
from perception.percept_state import PerceptState
from perception.screen_capture import ScreenCapture
from perception.window_tracker import WindowTracker
from utils.logger import get_logger

log = get_logger(__name__)

_PERCEPTION_PROMPT = """You are a screen-reading assistant.
Describe the current screen state in JSON with this exact structure:
{
  "description": "1-2 sentence plain summary of what is on screen",
  "app": "name of the focused application",
  "ui_elements": [{"type": "button|textbox|link|menu|text", "label": "...", "location": "top-left|center|..."}],
  "text_visible": "key text content visible on screen (max 300 chars)"
}
Return only the JSON, no extra text."""


class VisionAnalyzer:

    def __init__(self, vision_llm: LLMProvider | None, ocr: OCREngine):
        self._llm = vision_llm
        self._ocr = ocr
        self._capture = ScreenCapture()
        self._windows = WindowTracker()

    def analyze(self) -> PerceptState:
        """Capture screen and return a PerceptState."""
        img = self._capture.capture()
        window_title, pid = self._windows.get_active_window()

        state = PerceptState(
            screenshot=img,
            active_window=window_title,
            active_pid=pid,
            timestamp=time.time(),
        )

        if self._llm and self._llm.supports_vision():
            state.vision_description = self._analyze_with_vision(img)
        else:
            # Fallback: OCR
            state.ocr_text = self._ocr.extract_text(img)
            if state.ocr_text:
                state.vision_description = f"[OCR] {state.ocr_text[:400]}"
            else:
                state.vision_description = f"Window: {window_title}"

        log.debug(f"Perception: {state.vision_description[:100]}")
        return state

    def _analyze_with_vision(self, img: Image.Image) -> str:
        try:
            import json
            messages = [
                system_message("You analyze screenshots and return JSON only."),
                vision_message("user", _PERCEPTION_PROMPT, [img]),
            ]
            raw = self._llm.generate(messages)
            # Strip markdown code fences if present
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)
            return data.get("description", raw)
        except Exception as e:
            log.warning(f"Vision analysis failed: {e}")
            return f"Window: {self._windows.get_active_window()[0]}"
