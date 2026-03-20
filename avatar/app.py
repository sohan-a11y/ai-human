"""
Avatar UI — a small floating window showing the AI's face and current thought.
Runs in the main thread (Tkinter requirement).
Consumes events from EventBus via after() polling (thread-safe).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext

from core.event_bus import EventBus
from avatar.face import FaceWidget
from avatar.emotion_mapper import state_to_emotion
from utils.logger import get_logger

log = get_logger(__name__)


class AvatarApp:

    def __init__(self, event_bus: EventBus, on_goal_submit):
        self._bus = event_bus
        self._on_goal_submit = on_goal_submit

        self._root = tk.Tk()
        self._root.title("AI Human")
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)
        self._root.configure(bg="#1a1a2e")

        self._build_ui()
        self._poll()

    def _build_ui(self) -> None:
        # Face
        self._face = FaceWidget(self._root)
        self._face.pack(pady=(10, 5))

        # Status label
        self._status_var = tk.StringVar(value="Idle  (•‿•)")
        tk.Label(
            self._root, textvariable=self._status_var,
            bg="#1a1a2e", fg="#00d4ff", font=("Courier", 11, "bold")
        ).pack()

        # Thought bubble
        self._thought = scrolledtext.ScrolledText(
            self._root, height=5, width=40, bg="#0f3460", fg="#e0e0e0",
            font=("Courier", 9), wrap=tk.WORD, state=tk.DISABLED,
        )
        self._thought.pack(padx=10, pady=5)

        # Goal input
        frame = tk.Frame(self._root, bg="#1a1a2e")
        frame.pack(fill="x", padx=10, pady=(0, 10))

        self._goal_entry = tk.Entry(
            frame, bg="#16213e", fg="white", insertbackground="white",
            font=("Courier", 10), width=32,
        )
        self._goal_entry.pack(side="left", padx=(0, 5))
        self._goal_entry.bind("<Return>", self._submit_goal)

        tk.Button(
            frame, text="Go", command=self._submit_goal,
            bg="#00d4ff", fg="#1a1a2e", font=("Courier", 10, "bold"), width=4,
        ).pack(side="left")

    def _submit_goal(self, _event=None) -> None:
        goal = self._goal_entry.get().strip()
        if goal:
            self._goal_entry.delete(0, tk.END)
            self._on_goal_submit(goal)

    def _poll(self) -> None:
        """Poll event bus every 100ms — the safe cross-thread update pattern."""
        for event in self._bus.consume_all():
            self._handle_event(event)
        self._root.after(100, self._poll)

    def _handle_event(self, event) -> None:
        if event.type == "state_change":
            emotion, label = state_to_emotion(event.data)
            self._face.set_emotion(emotion)
            self._status_var.set(label)

        elif event.type in ("thought", "percept", "action", "error", "done", "goal"):
            msg = event.data
            if isinstance(msg, dict):
                msg = f"{msg.get('name','?')}: {'OK' if msg.get('success') else 'FAIL'} — {msg.get('msg','')}"
            self._append_thought(f"[{event.type}] {msg}")

    def _append_thought(self, text: str) -> None:
        self._thought.configure(state=tk.NORMAL)
        self._thought.insert(tk.END, text[:120] + "\n")
        self._thought.see(tk.END)
        self._thought.configure(state=tk.DISABLED)

    def run(self) -> None:
        self._root.mainloop()
