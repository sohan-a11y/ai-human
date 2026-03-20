"""
ActionExecutor — dispatches action names to their implementations.
All calls pass through SafetyBroker before reaching here.
"""

from __future__ import annotations

import pyautogui
from actions.base import ActionResult
from utils.logger import get_logger

log = get_logger(__name__)

# Disable pyautogui failsafe pause between actions (we handle safety ourselves)
pyautogui.PAUSE = 0.05


class ActionExecutor:

    def execute(self, action_name: str, args: dict) -> ActionResult:
        log.info(f"Action: {action_name} | args: {args}")
        handler = getattr(self, f"_do_{action_name}", None)
        if handler is None:
            return ActionResult(success=False, message=f"Unknown action: {action_name}")
        try:
            return handler(**args)
        except Exception as e:
            log.error(f"Action {action_name} failed: {e}")
            return ActionResult(success=False, message=str(e))

    # ── Mouse ────────────────────────────────────────────────────────────────

    def _do_click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> ActionResult:
        pyautogui.click(x, y, button=button, clicks=clicks, interval=0.1)
        return ActionResult(True, f"Clicked ({x},{y})")

    def _do_move(self, x: int, y: int) -> ActionResult:
        pyautogui.moveTo(x, y, duration=0.2)
        return ActionResult(True, f"Moved to ({x},{y})")

    def _do_drag(self, x1: int, y1: int, x2: int, y2: int) -> ActionResult:
        pyautogui.drag(x1 - x2, y1 - y2, duration=0.4, button="left")
        return ActionResult(True, f"Dragged ({x1},{y1}) → ({x2},{y2})")

    def _do_scroll(self, x: int, y: int, amount: int = 3) -> ActionResult:
        pyautogui.scroll(amount, x=x, y=y)
        return ActionResult(True, f"Scrolled {amount} at ({x},{y})")

    # ── Keyboard ─────────────────────────────────────────────────────────────

    def _do_type(self, text: str, interval: float = 0.02) -> ActionResult:
        pyautogui.typewrite(text, interval=interval)
        return ActionResult(True, f"Typed: {text[:40]}")

    def _do_hotkey(self, keys: list[str]) -> ActionResult:
        pyautogui.hotkey(*keys)
        return ActionResult(True, f"Hotkey: {'+'.join(keys)}")

    def _do_key(self, key: str) -> ActionResult:
        pyautogui.press(key)
        return ActionResult(True, f"Key: {key}")

    # ── Clipboard ────────────────────────────────────────────────────────────

    def _do_clipboard_copy(self) -> ActionResult:
        pyautogui.hotkey("ctrl", "c")
        import time; time.sleep(0.2)
        import pyperclip
        text = pyperclip.paste()
        return ActionResult(True, f"Copied: {text[:60]}", {"text": text})

    def _do_clipboard_paste(self, text: str | None = None) -> ActionResult:
        if text:
            import pyperclip
            pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        return ActionResult(True, "Pasted from clipboard")

    # ── File operations ──────────────────────────────────────────────────────

    def _do_read_file(self, path: str) -> ActionResult:
        from pathlib import Path
        try:
            content = Path(path).read_text(encoding="utf-8", errors="replace")
            return ActionResult(True, f"Read {path}", {"content": content})
        except Exception as e:
            return ActionResult(False, str(e))

    def _do_write_file(self, path: str, content: str) -> ActionResult:
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(content, encoding="utf-8")
        return ActionResult(True, f"Wrote {path}")

    def _do_delete_file(self, path: str) -> ActionResult:
        from pathlib import Path
        Path(path).unlink()
        return ActionResult(True, f"Deleted {path}")

    # ── Process ──────────────────────────────────────────────────────────────

    def _do_run_command(self, command: str, timeout: int = 30) -> ActionResult:
        import subprocess, shlex
        # SECURITY: never shell=True with user input -- prevents injection
        args = shlex.split(command) if isinstance(command, str) else list(command)
        if not args:
            return ActionResult(False, "Empty command")
        result = subprocess.run(args, shell=False, capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        return ActionResult(
            result.returncode == 0,
            f"Exit {result.returncode}: {output[:200]}",
            {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode},
        )

    def _do_open_app(self, path: str) -> ActionResult:
        import subprocess
        from pathlib import Path
        # SECURITY: resolve path, no shell expansion
        resolved = str(Path(path).resolve())
        subprocess.Popen([resolved], shell=False)
        return ActionResult(True, f"Opened: {path}")

    # ── Screenshot ───────────────────────────────────────────────────────────

    def _do_screenshot(self, save_path: str = "data/artifacts/screenshot.png") -> ActionResult:
        from perception.screen_capture import ScreenCapture
        from pathlib import Path
        img = ScreenCapture().capture()
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
        return ActionResult(True, f"Screenshot saved: {save_path}", {"path": save_path})

    # ── Wait ─────────────────────────────────────────────────────────────────

    def _do_wait(self, seconds: float = 1.0) -> ActionResult:
        import time
        time.sleep(seconds)
        return ActionResult(True, f"Waited {seconds}s")
