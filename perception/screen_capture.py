"""
Multi-monitor screenshot using mss.
Supports all monitors — captures primary by default, or any specific monitor,
or all monitors as a combined panorama.
"""

from __future__ import annotations

import mss
import mss.tools
from PIL import Image

from utils.logger import get_logger

log = get_logger(__name__)


class ScreenCapture:

    def __init__(self):
        self._monitor_count = self._get_monitor_count()
        log.info(f"Detected {self._monitor_count} monitor(s)")

    def _get_monitor_count(self) -> int:
        try:
            with mss.mss() as sct:
                return len(sct.monitors) - 1  # index 0 is the virtual combined screen
        except Exception:
            return 1

    @property
    def monitor_count(self) -> int:
        return self._monitor_count

    def capture(self, monitor: int = 1) -> Image.Image:
        """
        Capture screenshot of specified monitor.
        monitor=0 → all monitors combined into one image
        monitor=1 → primary (default)
        monitor=2 → second monitor, etc.
        """
        with mss.mss() as sct:
            monitors = sct.monitors
            # monitors[0] = virtual combined screen, monitors[1..n] = individual
            if monitor < 0 or monitor >= len(monitors):
                monitor = 1
            raw = sct.grab(monitors[monitor])
            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return img

    def capture_all_monitors(self) -> list[Image.Image]:
        """Capture all monitors as separate images."""
        images = []
        for i in range(1, self._monitor_count + 1):
            images.append(self.capture(i))
        return images

    def capture_combined(self) -> Image.Image:
        """Capture all monitors stitched into one wide image."""
        return self.capture(monitor=0)

    def capture_region(self, x: int, y: int, w: int, h: int) -> Image.Image:
        """Capture a specific region of the screen (coordinates in virtual space)."""
        with mss.mss() as sct:
            region = {"top": y, "left": x, "width": w, "height": h}
            raw = sct.grab(region)
            return Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")

    def get_monitor_info(self) -> list[dict]:
        """Returns info about each monitor: index, position, size."""
        with mss.mss() as sct:
            return [
                {"index": i, "left": m["left"], "top": m["top"],
                 "width": m["width"], "height": m["height"]}
                for i, m in enumerate(sct.monitors)
            ]
