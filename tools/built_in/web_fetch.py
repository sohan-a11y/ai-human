"""Fetch a URL and return clean text content."""

from __future__ import annotations

from tools.base_tool import BaseTool


class WebFetchTool(BaseTool):
    name = "web_fetch"
    description = "Fetch the content of a URL and return clean readable text."
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "max_chars": {"type": "integer", "default": 3000},
        },
        "required": ["url"],
    }

    def run(self, url: str, max_chars: int = 3000) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {"User-Agent": "Mozilla/5.0 (compatible; AIHuman/1.0)"}
            resp = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, "lxml")

            # Remove scripts, styles, nav noise
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)
            lines = [l for l in text.splitlines() if len(l.strip()) > 20]
            return "\n".join(lines)[:max_chars]
        except Exception as e:
            return f"Fetch failed: {e}"
