"""
Anthropic (Claude) provider.
Translates the unified message format to Anthropic SDK format,
including vision messages with images.
"""

from __future__ import annotations

import base64
from typing import Iterator

import anthropic
from llm.base import LLMProvider
from utils.logger import get_logger

log = get_logger(__name__)

_VISION_MODELS = {"claude-sonnet", "claude-opus", "claude-haiku"}


class AnthropicProvider(LLMProvider):

    def __init__(self, api_key: str, model: str, context_window: int = 100000, max_tokens: int = 1024):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._context = context_window
        self._max_tokens = max_tokens
        log.info(f"Anthropic provider | model={model}")

    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """Split system message from the rest, convert vision content."""
        system = ""
        converted = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"] if isinstance(msg["content"], str) else ""
                continue
            content = msg["content"]
            if isinstance(content, list):
                # Convert OpenAI image_url format → Anthropic image format
                parts = []
                for part in content:
                    if part["type"] == "image_url":
                        url = part["image_url"]["url"]
                        if url.startswith("data:image/"):
                            media_type, b64data = url.split(";base64,")
                            media_type = media_type.replace("data:", "")
                            parts.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": media_type, "data": b64data},
                            })
                    elif part["type"] == "text":
                        parts.append({"type": "text", "text": part["text"]})
                content = parts
            converted.append({"role": msg["role"], "content": content})
        return system, converted

    def generate(self, messages: list[dict], **kwargs) -> str:
        system, converted = self._convert_messages(messages)
        resp = self._client.messages.create(
            model=self._model,
            system=system,
            messages=converted,
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
        )
        return resp.content[0].text

    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        system, converted = self._convert_messages(messages)
        with self._client.messages.stream(
            model=self._model,
            system=system,
            messages=converted,
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
        ) as stream:
            for text in stream.text_stream:
                yield text

    def embed(self, text: str) -> list[float]:
        # Anthropic has no embeddings API — use local fallback
        from llm.openai_provider import _local_embed
        return _local_embed(text)

    def supports_vision(self) -> bool:
        model_lower = self._model.lower()
        return any(v in model_lower for v in _VISION_MODELS)

    @property
    def context_window(self) -> int:
        return self._context

    @property
    def model_name(self) -> str:
        return self._model
