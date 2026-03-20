"""
Episodic memory — every action, perception, and outcome stored forever.
No truncation. AI recalls as much as it needs via semantic search.
"""

from __future__ import annotations

import time
import uuid
from memory.vector_store import VectorStore

COLLECTION = "episodic"


class EpisodicMemory:

    def __init__(self, store: VectorStore):
        self._store = store

    def store(self, perception: str, action: str, outcome: str, goal: str = "") -> None:
        doc_id = str(uuid.uuid4())
        text = f"Goal: {goal}\nPerception: {perception}\nAction: {action}\nOutcome: {outcome}"
        self._store.upsert(COLLECTION, doc_id, text, {
            "timestamp": time.time(),
            "goal": goal[:200],
            "action": action[:200],
            "success": "failed" not in outcome.lower(),
        })

    def recall(self, query: str, n: int = 20) -> list[dict]:
        return self._store.query(COLLECTION, query, n)

    def recall_all(self) -> list[dict]:
        return self._store.query_all(COLLECTION)

    def recall_failures(self, query: str) -> list[dict]:
        items = self.recall(query, n=50)
        return [i for i in items if not i.get("metadata", {}).get("success", True)]

    def format_for_context(self, query: str, n: int = 10) -> str:
        items = self.recall(query, n)
        if not items:
            return ""
        lines = ["## Relevant past experience:"]
        for item in items:
            lines.append(f"- {item['text'][:400]}")
        return "\n".join(lines)

    def total_count(self) -> int:
        return self._store.count(COLLECTION)
