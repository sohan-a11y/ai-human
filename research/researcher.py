"""
ResearchOrchestrator — when the agent encounters something it doesn't know,
it uses this to search the web, read pages, and build structured knowledge.
Results are stored in semantic memory for future use.
"""

from __future__ import annotations

from llm.base import LLMProvider
from llm.message_builder import system_message, text_message
from tools.built_in.web_search import WebSearchTool
from tools.built_in.web_fetch import WebFetchTool
from memory.semantic import SemanticMemory
from utils.logger import get_logger

log = get_logger(__name__)

_RESEARCH_SYSTEM = """You are a research assistant. Given a topic or question, you:
1. Identify 3 key sub-questions to answer
2. Synthesize information into a concise, factual summary
Be direct and factual. No filler text."""


class ResearchOrchestrator:

    def __init__(self, llm: LLMProvider, semantic_memory: SemanticMemory):
        self._llm = llm
        self._memory = semantic_memory
        self._search = WebSearchTool()
        self._fetch = WebFetchTool()

    def research(self, topic: str, store_result: bool = True) -> str:
        """
        Full research pipeline: search → read top pages → synthesize.
        Returns a summary string. Also stores in semantic memory.
        """
        log.info(f"Researching: {topic}")

        # Check memory first
        cached = self._memory.recall(topic, n=1)
        if cached and cached[0]["distance"] < 0.3:
            log.info("Found cached knowledge — skipping web search")
            return cached[0]["text"]

        # Step 1: search
        search_results = self._search.run(query=topic, max_results=5)
        if "Search failed" in search_results or not search_results.strip():
            return f"Could not find information about: {topic}"

        # Step 2: fetch top 2 results
        urls = self._extract_urls(search_results)
        page_content = []
        for url in urls[:2]:
            content = self._fetch.run(url=url, max_chars=2000)
            if "Fetch failed" not in content:
                page_content.append(f"Source: {url}\n{content}")

        # Step 3: synthesize
        context = f"Search results:\n{search_results}\n\n"
        if page_content:
            context += "Page content:\n" + "\n\n---\n\n".join(page_content)

        messages = [
            system_message(_RESEARCH_SYSTEM),
            text_message("user", f"Research this topic and write a concise summary:\n\nTopic: {topic}\n\n{context}"),
        ]

        summary = self._llm.generate(messages)
        log.info(f"Research complete: {len(summary)} chars")

        if store_result and summary:
            self._memory.store(summary, source=f"research:{topic}", tags=["research", topic])

        return summary

    def _extract_urls(self, search_text: str) -> list[str]:
        import re
        return re.findall(r"https?://[^\s\n]+", search_text)
