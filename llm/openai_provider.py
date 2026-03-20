"""
OpenAI provider — also serves as the base for any OpenAI-compatible endpoint
(Ollama, LM Studio, custom local servers).

All local GGUF-quantized model servers expose /v1/chat/completions.
We just point base_url at the right port.
"""

from __future__ import annotations

from typing import Iterator

from openai import OpenAI
from llm.base import LLMProvider
from utils.logger import get_logger

log = get_logger(__name__)

# Vision-capable model name fragments
_VISION_MODELS = {"gpt-4o", "gpt-4-turbo", "llava", "moondream", "minicpm", "vision", "bakllava"}


class OpenAIProvider(LLMProvider):

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        context_window: int = 4096,
        max_tokens: int = 1024,
    ):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._context = context_window
        self._max_tokens = max_tokens
        log.info(f"OpenAI provider | model={model} | base_url={base_url or 'default'}")

    def generate(self, messages: list[dict], **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
            temperature=kwargs.get("temperature", 0.3),
        )
        return resp.choices[0].message.content or ""

    def stream(self, messages: list[dict], **kwargs) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", self._max_tokens),
            temperature=kwargs.get("temperature", 0.3),
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def embed(self, text: str) -> list[float]:
        # Ollama / LM Studio may not support embeddings API.
        # Fall back to a sentence-transformers local embed if available.
        try:
            resp = self._client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
            )
            return resp.data[0].embedding
        except Exception:
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


def _local_embed(text: str) -> list[float]:
    """
    Fallback embedding using sentence-transformers (all-MiniLM-L6-v2, 80 MB).
    Only imported if the OpenAI embeddings API call fails.
    """
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model.encode(text).tolist()
    except ImportError:
        # Last resort: return a zero vector (memory won't rank well but won't crash)
        log.warning("sentence-transformers not installed. Embeddings disabled.")
        return [0.0] * 384
