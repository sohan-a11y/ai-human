"""Track the active foreground window title and PID (Windows)."""

from __future__ import annotations

from utils.logger import get_logger

log = get_logger(__name__)


class WindowTracker:

    def get_active_window(self) -> tuple[str, int]:
        """Returns (window_title, pid)."""
        try:
            import win32gui
            import win32process
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return title, pid
        except ImportError:
            log.warning("pywin32 not installed — window tracking disabled")
            return "Unknown", 0
        except Exception as e:
            log.debug(f"Window tracking error: {e}")
            return "Unknown", 0
