"""
OCR fallback using pytesseract.
Used when no vision-capable LLM is available (fully offline low-RAM mode).
"""

from __future__ import annotations

from PIL import Image
from utils.logger import get_logger

log = get_logger(__name__)


class OCREngine:

    def __init__(self):
        self._available = self._check()

    def _check(self) -> bool:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            log.warning("Tesseract not found. OCR disabled. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
            return False

    def extract_text(self, img: Image.Image) -> str:
        if not self._available:
            return ""
        try:
            import pytesseract
            return pytesseract.image_to_string(img)
        except Exception as e:
            log.warning(f"OCR failed: {e}")
            return ""

    @property
    def available(self) -> bool:
        return self._available
