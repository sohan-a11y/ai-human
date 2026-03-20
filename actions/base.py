"""Action ABC — all agent actions implement this interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ActionResult:
    success: bool
    message: str
    data: dict | None = None


class Action(ABC):
    @abstractmethod
    def execute(self, **kwargs) -> ActionResult:
        ...

    @property
    @abstractmethod
    def risk_level(self) -> int:
        """Risk score 0-10. 0=safe, 10=destructive."""
        ...
