"""BaseTool interface. All tools (built-in and AI-created) must inherit this."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: dict = {}   # JSON Schema for args

    @abstractmethod
    def run(self, **kwargs) -> str:
        """Execute the tool. Returns a string result."""
