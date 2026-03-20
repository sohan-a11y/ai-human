"""Clipboard Manager skill pack — history, monitoring, rich clipboard operations."""

import time
from tools.base_tool import BaseTool


class ClipboardGetTool(BaseTool):
    name = "clipboard_get"
    description = "Get current clipboard content (text)."
    parameters = {"type": "object", "properties": {}}

    def run(self) -> str:
        try:
            import pyperclip
            content = pyperclip.paste()
            return content if content else "(clipboard empty)"
        except Exception as e:
            return f"Error: {e}"


class ClipboardSetTool(BaseTool):
    name = "clipboard_set"
    description = "Set clipboard content to specified text."
    parameters = {"type": "object", "properties": {
        "text": {"type": "string", "description": "Text to copy to clipboard"},
    }, "required": ["text"]}

    def run(self, text: str) -> str:
        try:
            import pyperclip
            pyperclip.copy(text)
            return f"Copied {len(text)} chars to clipboard."
        except Exception as e:
            return f"Error: {e}"


class ClipboardHistoryTool(BaseTool):
    name = "clipboard_history"
    description = "Get or manage clipboard history. Tracks last N clipboard entries."
    parameters = {"type": "object", "properties": {
        "action": {"type": "string", "enum": ["show", "clear", "paste_entry"],
                   "default": "show"},
        "entry_index": {"type": "integer", "default": 0,
                       "description": "Index of history entry to paste (for paste_entry action)"},
        "max_entries": {"type": "integer", "default": 20},
    }, "required": []}

    _history: list[dict] = []

    @classmethod
    def add_to_history(cls, text: str) -> None:
        if text and (not cls._history or cls._history[-1]["text"] != text):
            cls._history.append({"text": text, "time": time.time()})
            if len(cls._history) > 100:
                cls._history = cls._history[-100:]

    def run(self, action: str = "show", entry_index: int = 0, max_entries: int = 20) -> str:
        if action == "clear":
            self._history.clear()
            return "Clipboard history cleared."
        if action == "paste_entry":
            if 0 <= entry_index < len(self._history):
                try:
                    import pyperclip
                    pyperclip.copy(self._history[entry_index]["text"])
                    return f"Entry {entry_index} copied to clipboard."
                except Exception as e:
                    return f"Error: {e}"
            return f"Invalid index {entry_index}. History has {len(self._history)} entries."
        # show
        if not self._history:
            return "No clipboard history yet."
        lines = [f"Clipboard history ({len(self._history)} entries):"]
        for i, entry in enumerate(self._history[-max_entries:]):
            preview = entry["text"][:80].replace("\n", " ")
            lines.append(f"  [{i}] {preview}")
        return "\n".join(lines)


class ClipboardWatchTool(BaseTool):
    name = "clipboard_watch"
    description = "Watch clipboard for changes for N seconds, recording all copied text."
    parameters = {"type": "object", "properties": {
        "duration": {"type": "integer", "default": 30, "description": "Watch duration in seconds"},
    }, "required": []}

    def run(self, duration: int = 30) -> str:
        try:
            import pyperclip
            captured = []
            last = pyperclip.paste()
            end_time = time.time() + min(duration, 120)
            while time.time() < end_time:
                current = pyperclip.paste()
                if current != last:
                    captured.append(current)
                    ClipboardHistoryTool.add_to_history(current)
                    last = current
                time.sleep(0.5)
            if not captured:
                return f"No clipboard changes detected in {duration}s."
            return f"Captured {len(captured)} clipboard changes:\n" + "\n---\n".join(
                c[:200] for c in captured)
        except Exception as e:
            return f"Error: {e}"
