"""
LLMFactory — reads config, detects hardware, returns the right LLMProvider.
This is the only place in the codebase that knows about concrete provider classes.
"""

from __future__ import annotations

from config import Config
from llm.base import LLMProvider
from utils.hardware import detect_hardware, recommend_model
from utils.logger import get_logger

log = get_logger(__name__)


def create_llm(config: Config, model_type: str = "text") -> LLMProvider:
    """
    Create an LLMProvider based on config and hardware.

    model_type: 'text' or 'vision'
    """
    provider = config.llm_provider.lower()
    if model_type == "vision":
        provider = config.effective_vision_provider.lower()

    # Determine model name
    model = config.llm_model
    if model_type == "vision":
        model = config.vision_model or ""

    # Auto-select model based on hardware if not specified
    if not model:
        model, auto_ctx = recommend_model(provider, model_type)
        ctx = config.context_window or auto_ctx
    else:
        ctx = config.context_window or 4096

    max_tokens = config.max_tokens

    log.info(f"Creating provider: {provider} | model: {model} | context: {ctx}")

    if provider == "anthropic":
        from llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=config.anthropic_api_key,
            model=model,
            context_window=ctx,
            max_tokens=max_tokens,
        )

    elif provider == "openai":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model=model,
            context_window=ctx,
            max_tokens=max_tokens,
        )

    elif provider == "ollama":
        from llm.ollama_provider import OllamaProvider
        p = OllamaProvider(
            model=model,
            base_url=config.ollama_base_url,
            context_window=ctx,
            max_tokens=max_tokens,
        )
        # Auto-pull model if not present
        if not p.is_model_available():
            log.warning(f"Model '{model}' not found in Ollama. Pulling now...")
            p.pull_model()
        return p

    elif provider == "lmstudio":
        from llm.lmstudio_provider import LMStudioProvider
        return LMStudioProvider(
            model=model,
            base_url=config.lmstudio_base_url,
            context_window=ctx,
            max_tokens=max_tokens,
        )

    elif provider == "custom":
        from llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=config.custom_api_key,
            model=config.custom_model or model,
            base_url=config.custom_base_url,
            context_window=ctx,
            max_tokens=max_tokens,
        )

    else:
        raise ValueError(
            f"Unknown provider: '{provider}'. "
            f"Valid options: anthropic, openai, ollama, lmstudio, custom"
        )
