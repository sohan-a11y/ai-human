"""
AskAI Tool — when the agent can't figure something out, it opens a browser,
goes to ChatGPT (no login required via chatgpt.com), asks the question,
waits for the answer, and returns it.

Fallback chain:
  1. ChatGPT (chatgpt.com — no login needed for basic questions)
  2. Google search + read top result
  3. DuckDuckGo + read top result
"""

from __future__ import annotations

import time
from tools.base_tool import BaseTool
from utils.logger import get_logger

log = get_logger(__name__)


class AskAITool(BaseTool):
    name = "ask_ai"
    description = (
        "When you don't know how to do something, use this tool to ask ChatGPT. "
        "It opens a browser, sends your question to ChatGPT, and returns the answer. "
        "No login required."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The question to ask ChatGPT"},
            "context": {"type": "string", "description": "Extra context about what you're trying to do"},
        },
        "required": ["question"],
    }

    def run(self, question: str, context: str = "") -> str:
        full_question = question
        if context:
            full_question = f"{question}\n\nContext: {context}"

        # Try ChatGPT first
        result = self._ask_chatgpt(full_question)
        if result and len(result) > 50:
            return result

        # Fallback: Google search
        log.info("ChatGPT failed, falling back to Google search")
        return self._google_search(question)

    def _ask_chatgpt(self, question: str) -> str:
        """Open ChatGPT in browser, type question, wait for answer, return it."""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # visible so user can see
                page = browser.new_page()

                log.info("Opening ChatGPT...")
                page.goto("https://chatgpt.com", timeout=15000)
                page.wait_for_timeout(3000)

                # Find the message input (works without login)
                selectors = [
                    "#prompt-textarea",
                    "textarea[placeholder*='Message']",
                    "textarea[placeholder*='Ask']",
                    "div[contenteditable='true']",
                ]

                input_el = None
                for sel in selectors:
                    try:
                        el = page.wait_for_selector(sel, timeout=5000)
                        if el:
                            input_el = el
                            break
                    except Exception:
                        continue

                if not input_el:
                    browser.close()
                    return ""

                # Type the question
                input_el.click()
                page.keyboard.type(question, delay=30)
                page.wait_for_timeout(500)
                page.keyboard.press("Enter")

                # Wait for response (up to 60 seconds)
                log.info("Waiting for ChatGPT response...")
                response_text = self._wait_for_chatgpt_response(page, timeout=60)

                browser.close()
                return response_text

        except ImportError:
            log.warning("playwright not installed — run: pip install playwright && playwright install chromium")
            return ""
        except Exception as e:
            log.warning(f"ChatGPT query failed: {e}")
            return ""

    def _wait_for_chatgpt_response(self, page, timeout: int = 60) -> str:
        """Wait for ChatGPT to finish generating and return the response text."""
        start = time.time()
        last_text = ""
        stable_count = 0

        while time.time() - start < timeout:
            time.sleep(2)
            try:
                # ChatGPT response selectors
                response_els = page.query_selector_all(
                    "div[data-message-author-role='assistant'], .markdown, article"
                )
                if response_els:
                    current_text = response_els[-1].inner_text()
                    if current_text == last_text and len(current_text) > 50:
                        stable_count += 1
                        if stable_count >= 2:  # stable for 4 seconds = done
                            return current_text[:3000]
                    else:
                        stable_count = 0
                    last_text = current_text
            except Exception:
                pass

        return last_text[:3000] if last_text else ""

    def _google_search(self, question: str) -> str:
        """Fallback: search Google and return top result text."""
        try:
            import requests
            from bs4 import BeautifulSoup

            url = f"https://www.google.com/search?q={requests.utils.quote(question)}"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "lxml")

            # Featured snippet
            snippet = soup.select_one(".hgKElc, .ILfuVd, .yDYNvb")
            if snippet:
                return f"Google answer: {snippet.get_text(strip=True)}"

            # First result
            result = soup.select_one(".g .VwiC3b")
            if result:
                return f"Google result: {result.get_text(strip=True)}"

            return "Could not find an answer."
        except Exception as e:
            return f"Search failed: {e}"
