"""Structured logger using loguru with file rotation."""

from __future__ import annotations

import sys
from pathlib import Path
from loguru import logger


def _setup() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}")
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logger.add(log_dir / "aihuman_{time}.log", rotation="10 MB", retention="7 days", level="DEBUG", encoding="utf-8")


_setup()


def get_logger(name: str):
    return logger.bind(name=name)
