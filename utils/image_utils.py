"""PIL image helpers: resize, base64 encode for vision APIs."""

from __future__ import annotations

import base64
import io
from PIL import Image


def image_to_base64(img: Image.Image, format: str = "PNG", max_size: tuple[int, int] = (1280, 720)) -> str:
    """Encode a PIL image to base64 string, resizing if needed to save tokens."""
    img.thumbnail(max_size, Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def base64_to_image(b64: str) -> Image.Image:
    data = base64.b64decode(b64)
    return Image.open(io.BytesIO(data))


def load_image(path: str) -> Image.Image:
    return Image.open(path)
