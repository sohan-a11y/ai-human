"""
Semantic memory — learned facts, research, tool docs, knowledge — stored forever.
Everything is in ChromaDB on disk. Nothing is ever lost.
"""

from __future__ import annotations

import uuid
from memory.vector_store import VectorStore

COLLECTION = "semantic"


class SemanticMemory:

    def __init__(self, store: VectorStore):
        self._store = store

    def store(self, text: str, source: str = "", tags: list[str] | None = None) -> str:
        doc_id = str(uuid.uuid4())
        self._store.upsert(COLLECTION, doc_id, text, {
            "source": source,
            "tags": ",".join(tags or []),
        })
        return doc_id

    def recall(self, query: str, n: int = 20) -> list[dict]:
        return self._store.query(COLLECTION, query, n)

    def recall_all(self) -> list[dict]:
        return self._store.query_all(COLLECTION)

    def format_for_context(self, query: str, n: int = 10) -> str:
        items = self.recall(query, n)
        if not items:
            return ""
        lines = ["## Relevant knowledge:"]
        for item in items:
            src = item["metadata"].get("source", "")
            lines.append(f"- {item['text'][:400]}" + (f" (from: {src})" if src else ""))
        return "\n".join(lines)

    def total_count(self) -> int:
        return self._store.count(COLLECTION)
