"""
Playwright Browser Tool — reliable web automation.
Unlike pyautogui on a browser, Playwright directly controls the browser DOM.
Works on dynamic pages, SPAs, JS-heavy sites.

Supports:
- Navigate to URL
- Click elements by selector, text, or role
- Type into forms
- Extract page text/data
- Take screenshots
- Run JavaScript
"""

from __future__ import annotations

from tools.base_tool import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)

# Global persistent browser instance to avoid reopening on every call
_browser = None
_page = None
_playwright = None


def _get_page():
    global _browser, _page, _playwright
    try:
        from playwright.sync_api import sync_playwright
        if _playwright is None:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=False)
            _page = _browser.new_page()
            log.info("Playwright browser started")
        return _page
    except ImportError:
        raise RuntimeError("playwright not installed. Run: pip install playwright && playwright install chromium")


def close_browser():
    global _browser, _page, _playwright
    if _browser:
        _browser.close()
    if _playwright:
        _playwright.stop()
    _browser = _page = _playwright = None


class BrowserNavigateTool(BaseTool):
    name = "browser_navigate"
    description = "Open a URL in the browser. Use for web automation, filling forms, clicking links."
    parameters = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    }

    def run(self, url: str) -> str:
        try:
            page = _get_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            return f"Navigated to: {url} | Title: {page.title()}"
        except Exception as e:
            return f"Navigation failed: {e}"


class BrowserClickTool(BaseTool):
    name = "browser_click"
    description = "Click an element on the current web page. Provide text, selector, or role."
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Visible text of the element"},
            "selector": {"type": "string", "description": "CSS selector"},
            "role": {"type": "string", "description": "ARIA role e.g. button, link, textbox"},
        },
    }

    def run(self, text: str = "", selector: str = "", role: str = "") -> str:
        try:
            page = _get_page()
            if text:
                page.get_by_text(text, exact=False).first.click(timeout=5000)
            elif selector:
                page.click(selector, timeout=5000)
            elif role:
                page.get_by_role(role).first.click(timeout=5000)
            else:
                return "Provide text, selector, or role"
            return f"Clicked: {text or selector or role}"
        except Exception as e:
            return f"Click failed: {e}"


class BrowserTypeTool(BaseTool):
    name = "browser_type"
    description = "Type text into a form field on the current web page."
    parameters = {
        "type": "object",
        "properties": {
            "selector": {"type": "string", "description": "CSS selector of the input"},
            "text": {"type": "string"},
            "clear_first": {"type": "boolean", "default": True},
        },
        "required": ["selector", "text"],
    }

    def run(self, selector: str, text: str, clear_first: bool = True) -> str:
        try:
            page = _get_page()
            el = page.locator(selector).first
            if clear_first:
                el.clear()
            el.type(text, delay=30)
            return f"Typed into {selector}"
        except Exception as e:
            return f"Type failed: {e}"


class BrowserGetTextTool(BaseTool):
    name = "browser_get_text"
    description = "Extract all visible text from the current web page."
    parameters = {
        "type": "object",
        "properties": {"max_chars": {"type": "integer", "default": 3000}},
    }

    def run(self, max_chars: int = 3000) -> str:
        try:
            page = _get_page()
            text = page.inner_text("body")
            lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 10]
            return "\n".join(lines)[:max_chars]
        except Exception as e:
            return f"Get text failed: {e}"


class BrowserRunJSTool(BaseTool):
    name = "browser_run_js"
    description = "Run JavaScript in the current browser page and return the result."
    parameters = {
        "type": "object",
        "properties": {"script": {"type": "string"}},
        "required": ["script"],
    }

    def run(self, script: str) -> str:
        try:
            page = _get_page()
            result = page.evaluate(script)
            return str(result)
        except Exception as e:
            return f"JS failed: {e}"


class BrowserScreenshotTool(BaseTool):
    name = "browser_screenshot"
    description = "Take a screenshot of the current browser page."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "default": "data/artifacts/browser.png"}},
    }

    def run(self, path: str = "data/artifacts/browser.png") -> str:
        try:
            from pathlib import Path
            page = _get_page()
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=path)
            return f"Screenshot saved: {path}"
        except Exception as e:
            return f"Screenshot failed: {e}"
