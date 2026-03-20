"""Canvas-drawn ASCII-style face with animated blink."""

from __future__ import annotations

import tkinter as tk
import random

FACES = {
    "idle":      "(•‿•)",
    "thinking":  "(•_•) ...",
    "acting":    "(⌐■_■)",
    "error":     "(ಠ_ಠ)",
    "done":      "(◕‿◕)",
    "perceiving":"(👁 ‿ 👁)",
}


class FaceWidget(tk.Label):

    def __init__(self, parent):
        super().__init__(
            parent,
            text=FACES["idle"],
            font=("Segoe UI Emoji", 28),
            bg="#1a1a2e",
            fg="#00d4ff",
        )
        self._current = "idle"
        self._blink()

    def set_emotion(self, emotion: str) -> None:
        self._current = emotion
        self.configure(text=FACES.get(emotion, FACES["idle"]))

    def _blink(self) -> None:
        if self._current == "idle":
            self.configure(text="(-‿-)")
            self.after(150, lambda: self.configure(text=FACES["idle"]))
        interval = random.randint(3000, 6000)
        self.after(interval, self._blink)
