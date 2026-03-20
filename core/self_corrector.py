"""
SelfCorrector — when an action fails, the agent thinks like a human:
  1. Understand what went wrong
  2. Search for a solution (web, ChatGPT, Google)
  3. Apply what was learned
  4. Retry with new knowledge
  5. Store the lesson in memory

This replaces the "give up on error" behavior with human-like persistence.
"""

from __future__ import annotations

from llm.base import LLMProvider
from llm.message_builder import system_message, text_message
from memory.semantic import SemanticMemory
from research.researcher import ResearchOrchestrator
from utils.logger import get_logger

log = get_logger(__name__)

_DIAGNOSE_PROMPT = """You are diagnosing a failure in a computer automation task.
Given the goal, the action that was tried, and the error, return JSON:
{
  "diagnosis": "what went wrong in plain English",
  "search_query": "web search query to find a solution",
  "alternative_approach": "describe a different way to accomplish the goal",
  "needs_human_help": false
}
Return only JSON."""


class SelfCorrector:

    def __init__(self, llm: LLMProvider, researcher: ResearchOrchestrator, semantic: SemanticMemory):
        self._llm = llm
        self._researcher = researcher
        self._semantic = semantic
        self._failure_counts: dict[str, int] = {}

    def handle_failure(
        self,
        goal: str,
        action_name: str,
        args: dict,
        error_message: str,
    ) -> dict:
        """
        Called when an action fails.
        Returns a correction plan: {"lesson": str, "new_approach": str, "search_result": str}
        """
        failure_key = f"{goal}:{action_name}"
        self._failure_counts[failure_key] = self._failure_counts.get(failure_key, 0) + 1
        count = self._failure_counts[failure_key]

        log.info(f"Handling failure #{count}: {action_name} — {error_message[:80]}")

        # Step 1: Diagnose
        diagnosis = self._diagnose(goal, action_name, args, error_message)
        search_query = diagnosis.get("search_query", f"how to {goal} on Windows")
        new_approach = diagnosis.get("alternative_approach", "")

        # Step 2: Research
        search_result = ""
        if count <= 3:  # Don't search forever
            log.info(f"Researching solution: {search_query}")
            search_result = self._researcher.research(search_query, store_result=True)

        # Step 3: Store the lesson
        lesson = f"When trying '{goal}', action '{action_name}' failed with: {error_message}. " \
                 f"Diagnosis: {diagnosis.get('diagnosis', '')}. Solution found: {search_result[:200]}"
        self._semantic.store(lesson, source="self_correction", tags=["failure", "lesson"])

        return {
            "lesson": lesson,
            "new_approach": new_approach,
            "search_result": search_result,
            "failure_count": count,
            "give_up": count > 5 and diagnosis.get("needs_human_help", False),
        }

    def _diagnose(self, goal: str, action: str, args: dict, error: str) -> dict:
        try:
            import json
            messages = [
                system_message(_DIAGNOSE_PROMPT),
                text_message("user", f"Goal: {goal}\nAction: {action}\nArgs: {args}\nError: {error}"),
            ]
            raw = self._llm.generate(messages)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            return json.loads(raw)
        except Exception as e:
            log.debug(f"Diagnosis parse failed: {e}")
            return {
                "diagnosis": error,
                "search_query": f"fix error: {error[:80]}",
                "alternative_approach": "",
                "needs_human_help": False,
            }
