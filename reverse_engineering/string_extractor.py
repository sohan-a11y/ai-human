"""
String extractor for binary files.
Extracts printable ASCII and Unicode (UTF-16LE) strings without requiring
any external tools — pure Python. Also integrates with 'strings' CLI if
available, and r2pipe for section-aware extraction.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ExtractedString:
    value: str
    offset: int
    encoding: str  # "ascii" | "utf16le" | "utf8"
    length: int
    section: str = ""
    category: str = ""  # "url", "path", "registry", "api", "credential_hint", "other"


# Patterns for categorization
_PATTERNS = {
    "url": re.compile(r"https?://[^\s\"'<>]{4,}", re.IGNORECASE),
    "path_win": re.compile(r"[A-Za-z]:\\[^\s\"]{3,}"),
    "path_unix": re.compile(r"/[a-z][a-zA-Z0-9/_\-.]{3,}"),
    "registry": re.compile(r"(HKEY_|HKLM\\|HKCU\\|SOFTWARE\\)[^\s\"]{3,}", re.IGNORECASE),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "api": re.compile(r"(VirtualAlloc|CreateProcess|WriteProcessMemory|ShellExecute|"
                      r"RegOpenKey|InternetOpen|URLDownloadToFile|WinExec|"
                      r"CreateRemoteThread|LoadLibrary|GetProcAddress)", re.IGNORECASE),
    "credential_hint": re.compile(r"(password|passwd|secret|token|apikey|api_key|"
                                   r"authorization|bearer|credential)", re.IGNORECASE),
}


class StringExtractor:
    """Extract human-readable strings from binary files."""

    def __init__(self, min_length: int = 4):
        self.min_length = min_length

    def extract(self, path: str) -> list[ExtractedString]:
        """Extract all strings from a binary file using pure Python."""
        data = Path(path).read_bytes()
        results: list[ExtractedString] = []
        results.extend(self._extract_ascii(data))
        results.extend(self._extract_utf16le(data))
        # Sort by offset
        results.sort(key=lambda s: s.offset)
        # Categorize
        for s in results:
            s.category = self._categorize(s.value)
        return results

    def extract_interesting(self, path: str) -> list[ExtractedString]:
        """Return only strings that are likely interesting (URLs, IPs, APIs, etc.)."""
        all_strings = self.extract(path)
        return [s for s in all_strings if s.category != "other"]

    def _extract_ascii(self, data: bytes) -> list[ExtractedString]:
        results = []
        i = 0
        start = -1
        buf = []

        while i < len(data):
            b = data[i]
            if 0x20 <= b <= 0x7E or b in (0x09, 0x0A, 0x0D):  # printable + whitespace
                if start == -1:
                    start = i
                buf.append(chr(b))
            else:
                if buf and len(buf) >= self.min_length:
                    value = "".join(buf).strip()
                    if len(value) >= self.min_length:
                        results.append(ExtractedString(
                            value=value,
                            offset=start,
                            encoding="ascii",
                            length=len(buf),
                        ))
                start = -1
                buf = []
            i += 1

        if buf and len(buf) >= self.min_length:
            value = "".join(buf).strip()
            if len(value) >= self.min_length:
                results.append(ExtractedString(
                    value=value, offset=start, encoding="ascii", length=len(buf)
                ))
        return results

    def _extract_utf16le(self, data: bytes) -> list[ExtractedString]:
        results = []
        i = 0
        start = -1
        chars = []

        while i + 1 < len(data):
            lo = data[i]
            hi = data[i + 1]
            if hi == 0x00 and 0x20 <= lo <= 0x7E:
                if start == -1:
                    start = i
                chars.append(chr(lo))
                i += 2
            else:
                if chars and len(chars) >= self.min_length:
                    value = "".join(chars).strip()
                    if len(value) >= self.min_length:
                        results.append(ExtractedString(
                            value=value,
                            offset=start,
                            encoding="utf16le",
                            length=len(chars),
                        ))
                start = -1
                chars = []
                i += 1

        if chars and len(chars) >= self.min_length:
            value = "".join(chars).strip()
            if len(value) >= self.min_length:
                results.append(ExtractedString(
                    value=value, offset=start, encoding="utf16le", length=len(chars)
                ))
        return results

    def _categorize(self, value: str) -> str:
        for category, pattern in _PATTERNS.items():
            if pattern.search(value):
                return category
        return "other"

    def summary(self, strings: list[ExtractedString]) -> dict:
        """Return a summary dict grouped by category."""
        from collections import defaultdict
        groups: dict[str, list[str]] = defaultdict(list)
        for s in strings:
            groups[s.category].append(s.value)
        return dict(groups)

    def to_text(self, strings: list[ExtractedString]) -> str:
        """Format extracted strings as readable text."""
        lines = []
        for s in strings:
            lines.append(f"[0x{s.offset:08X}] [{s.encoding:7}] [{s.category:16}] {s.value}")
        return "\n".join(lines)
