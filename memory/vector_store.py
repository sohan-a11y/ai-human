"""
ChromaDB embedded vector store — v0.5+ API.
No artificial limits. Everything is stored forever. AI retrieves what it needs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import chromadb

from utils.logger import get_logger

log = get_logger(__name__)


class VectorStore:

    def __init__(self, persist_dir: str, embed_fn: Callable[[str], list[float]]):
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        # ChromaDB v0.5+ uses PersistentClient (old Settings-based init removed)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._embed_fn = embed_fn
        log.info(f"VectorStore ready at {persist_dir}")

    def collection(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, collection_name: str, doc_id: str, text: str, metadata: dict | None = None) -> None:
        col = self.collection(collection_name)
        embedding = self._embed_fn(text)
        col.upsert(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}],
        )

    def query(self, collection_name: str, query_text: str, n_results: int = 20) -> list[dict]:
        """Returns top n_results similar docs. No artificial cap — AI decides how many it needs."""
        col = self.collection(collection_name)
        count = col.count()
        if count == 0:
            return []
        embedding = self._embed_fn(query_text)
        results = col.query(query_embeddings=[embedding], n_results=min(n_results, count))
        return [
            {
                "text": results["documents"][0][i],
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else 0,
            }
            for i in range(len(results["documents"][0]))
        ]

    def query_all(self, collection_name: str) -> list[dict]:
        """Retrieve every record — for full recall when needed."""
        col = self.collection(collection_name)
        if col.count() == 0:
            return []
        results = col.get()
        return [
            {"text": results["documents"][i], "id": results["ids"][i], "metadata": results["metadatas"][i]}
            for i in range(len(results["documents"]))
        ]

    def delete(self, collection_name: str, doc_id: str) -> None:
        self.collection(collection_name).delete(ids=[doc_id])

    def count(self, collection_name: str) -> int:
        return self.collection(collection_name).count()
