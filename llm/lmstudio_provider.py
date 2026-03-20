"""
LM Studio provider — local GGUF models via LM Studio's OpenAI-compatible server.
Default port: 1234. Load any GGUF model in LM Studio UI and this will connect.
"""

from __future__ import annotations

from llm.openai_provider import OpenAIProvider
from utils.logger import get_logger

log = get_logger(__name__)


class LMStudioProvider(OpenAIProvider):

    def __init__(self, model: str, base_url: str = "http://localhost:1234", context_window: int = 4096, max_tokens: int = 1024):
        super().__init__(
            api_key="lm-studio",
            model=model,
            base_url=f"{base_url}/v1",
            context_window=context_window,
            max_tokens=max_tokens,
        )
        log.info(f"LM Studio provider | model={model} | url={base_url}")
