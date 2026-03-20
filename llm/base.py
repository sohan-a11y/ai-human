"""
Abstract base class for all LLM providers.
Every module in the system depends only on this interface, never on a concrete class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator


class LLMProvider(ABC):

    @abstractmethod
    def generate(self, messages: list[dict], **kwargs) -> str:
        """
        Synchronous text generation.
        messages: list of {"role": "user"|"assistant"|"system", "content": str | list}
        Returns the assistant reply as a plain string.
        """

    @abstractmethod
    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        """Streaming generation. Yields token strings as they arrive."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """
        Returns a dense embedding vector for the given text.
        Used by the vector memory store.
        If the provider does not support embeddings, raise NotImplementedError.
        """

    @abstractmethod
    def supports_vision(self) -> bool:
        """Returns True if this provider+model can process image content."""

    @property
    @abstractmethod
    def context_window(self) -> int:
        """Max token count this model supports."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Active model identifier string."""
