"""PerceptState: structured snapshot of what the agent currently sees."""

from __future__ import annotations

from dataclasses import dataclass, field
from PIL import Image


@dataclass
class PerceptState:
    screenshot: Image.Image | None = None
    ocr_text: str = ""
    vision_description: str = ""   # LLM's natural language description of the screen
    active_window: str = ""        # Title of the foreground window
    active_pid: int = 0
    ui_elements: list[dict] = field(default_factory=list)  # [{type, label, rect}]
    timestamp: float = 0.0

    def summary(self) -> str:
        """Short text summary for injecting into LLM context."""
        lines = []
        if self.active_window:
            lines.append(f"Active window: {self.active_window}")
        if self.vision_description:
            lines.append(f"Screen: {self.vision_description}")
        elif self.ocr_text:
            lines.append(f"Visible text: {self.ocr_text[:500]}")
        return "\n".join(lines) or "Screen: unknown"
