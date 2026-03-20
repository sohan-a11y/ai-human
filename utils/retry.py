"""Retry decorator with exponential backoff for flaky LLM/network calls."""

from __future__ import annotations

import time
import functools
from typing import Callable, Type

from utils.logger import get_logger

log = get_logger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            attempt = 0
            wait = delay
            while attempt < max_attempts:
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        raise
                    log.warning(f"{fn.__name__} failed (attempt {attempt}/{max_attempts}): {e}. Retrying in {wait:.1f}s")
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator
