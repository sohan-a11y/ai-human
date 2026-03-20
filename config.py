"""
Central configuration loaded from .env
All modules import from here — never from os.environ directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Provider
    llm_provider: str = Field(default="ollama")
    llm_model: str = Field(default="")

    # API keys
    anthropic_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")

    # Local provider URLs
    ollama_base_url: str = Field(default="http://localhost:11434")
    lmstudio_base_url: str = Field(default="http://localhost:1234")

    # Custom endpoint
    custom_base_url: str = Field(default="")
    custom_api_key: str = Field(default="")   # never set a fake default key
    custom_model: str = Field(default="")

    # Remote server authentication (generate a random token and set in .env)
    remote_api_token: str = Field(default="")  # set REMOTE_API_TOKEN in .env
    mobile_api_token: str = Field(default="")

    # Email credentials (for email skill pack)
    email_user: str = Field(default="")
    email_pass: str = Field(default="")

    # Database credentials (for database skill pack)
    postgres_password: str = Field(default="")
    mysql_password: str = Field(default="")

    # Vision
    vision_model: str = Field(default="")
    vision_provider: str = Field(default="")

    # Hardware overrides (0 = auto-detect)
    ram_gb: float = Field(default=0)
    vram_gb: float = Field(default=0)
    cpu_cores: int = Field(default=0)

    # Performance
    loop_interval_seconds: float = Field(default=3.0)
    max_tokens: int = Field(default=1024)
    context_window: int = Field(default=0)

    # Safety
    safety_confirm_threshold: int = Field(default=7)
    safety_block_threshold: int = Field(default=9)

    # Memory
    chroma_persist_dir: str = Field(default="data/chroma")
    max_memory_results: int = Field(default=5)

    # Avatar
    show_avatar: bool = Field(default=True)

    @property
    def chroma_path(self) -> Path:
        return Path(self.chroma_persist_dir)

    @property
    def effective_vision_provider(self) -> str:
        return self.vision_provider or self.llm_provider


# Singleton
_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
