"""
Build provider-agnostic message dicts consumed by all LLMProvider implementations.
Centralising message construction means providers only translate, never build structure.
"""

from __future__ import annotations

from PIL import Image
from utils.image_utils import image_to_base64


def text_message(role: str, content: str) -> dict:
    return {"role": role, "content": content}


def vision_message(role: str, text: str, images: list[Image.Image]) -> dict:
    """
    Builds a multi-part message with one or more images and text.
    Uses the OpenAI image_url format internally.
    Provider implementations convert this to their own schema.
    """
    parts = []
    for img in images:
        b64 = image_to_base64(img)
        parts.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    parts.append({"type": "text", "text": text})
    return {"role": role, "content": parts}


def system_message(content: str) -> dict:
    return {"role": "system", "content": content}


def assistant_message(content: str) -> dict:
    return {"role": "assistant", "content": content}
