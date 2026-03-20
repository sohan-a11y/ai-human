"""Thread-safe event bus for communication between agent, UI, and modules."""

from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    type: str       # e.g. "state_change", "action", "error", "thought"
    data: Any = None


class EventBus:

    def __init__(self):
        self._queue: queue.Queue[Event] = queue.Queue()

    def publish(self, event_type: str, data: Any = None) -> None:
        self._queue.put_nowait(Event(type=event_type, data=data))

    def consume(self, timeout: float = 0.05) -> Event | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def consume_all(self) -> list[Event]:
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return events
