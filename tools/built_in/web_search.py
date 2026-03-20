"""
Web search tool using DuckDuckGo — no API key required.
Works offline if results are cached in semantic memory.
"""

from __future__ import annotations

from tools.base_tool import BaseTool


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the internet for information. Returns a list of result titles and URLs."
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }

    def run(self, query: str, max_results: int = 5) -> str:
        try:
            import requests
            from bs4 import BeautifulSoup

            url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (compatible; AIHuman/1.0)"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            for result in soup.select(".result")[:max_results]:
                title_el = result.select_one(".result__title")
                url_el = result.select_one(".result__url")
                snippet_el = result.select_one(".result__snippet")
                if title_el:
                    results.append({
                        "title": title_el.get_text(strip=True),
                        "url": url_el.get_text(strip=True) if url_el else "",
                        "snippet": snippet_el.get_text(strip=True) if snippet_el else "",
                    })

            if not results:
                return "No results found."

            lines = [f"{i+1}. {r['title']}\n   {r['url']}\n   {r['snippet']}" for i, r in enumerate(results)]
            return "\n\n".join(lines)
        except Exception as e:
            return f"Search failed: {e}"
