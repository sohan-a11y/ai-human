"""
Ollama provider — local GGUF-quantized models via Ollama's OpenAI-compatible API.

Ollama serves /v1/chat/completions at http://localhost:11434
Supports CPU-only inference with quantized models (Q4_K_M etc.)
Runs models as small as TinyLlama 1.1B on 2 GB RAM.
"""

from __future__ import annotations

from typing import Iterator

from llm.openai_provider import OpenAIProvider
from utils.logger import get_logger

log = get_logger(__name__)

# Ollama vision-capable models
_VISION_MODELS = {"llava", "moondream", "minicpm", "bakllava", "llava-phi3"}


class OllamaProvider(OpenAIProvider):

    def __init__(self, model: str, base_url: str = "http://localhost:11434", context_window: int = 4096, max_tokens: int = 1024):
        super().__init__(
            api_key="ollama",           # Ollama ignores the key but openai client requires it
            model=model,
            base_url=f"{base_url}/v1",
            context_window=context_window,
            max_tokens=max_tokens,
        )
        self._ollama_base = base_url
        log.info(f"Ollama provider | model={model} | url={base_url}")

    def embed(self, text: str) -> list[float]:
        """Use Ollama's native /api/embeddings endpoint (no OpenAI embeddings API needed)."""
        import requests
        try:
            resp = requests.post(
                f"{self._ollama_base}/api/embeddings",
                json={"model": self._model, "prompt": text},
                timeout=30,
            )
            if resp.ok:
                return resp.json().get("embedding", [])
        except Exception as e:
            log.warning(f"Ollama embedding failed: {e}")
        from llm.openai_provider import _local_embed
        return _local_embed(text)

    def supports_vision(self) -> bool:
        model_lower = self._model.lower()
        return any(v in model_lower for v in _VISION_MODELS)

    def list_local_models(self) -> list[str]:
        """Returns list of models already pulled in Ollama."""
        import requests
        try:
            resp = requests.get(f"{self._ollama_base}/api/tags", timeout=5)
            if resp.ok:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    def is_model_available(self, model: str | None = None) -> bool:
        target = model or self._model
        return target in self.list_local_models()

    def pull_model(self, model: str | None = None) -> None:
        """Pull (download) a model if not already present. Shows progress."""
        import requests
        target = model or self._model
        log.info(f"Pulling Ollama model: {target}")
        with requests.post(
            f"{self._ollama_base}/api/pull",
            json={"name": target},
            stream=True,
            timeout=3600,
        ) as resp:
            for line in resp.iter_lines():
                if line:
                    import json
                    data = json.loads(line)
                    status = data.get("status", "")
                    if "total" in data:
                        done = data.get("completed", 0)
                        total = data["total"]
                        pct = int(done / total * 100) if total else 0
                        print(f"\r  {status}: {pct}%", end="", flush=True)
                    else:
                        print(f"  {status}")
        print()
        log.info(f"Model {target} ready.")
