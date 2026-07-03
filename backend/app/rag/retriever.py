"""RAG retrieval over the MMM methodology knowledge base (design doc 5.3).

Hybrid strategy:
  1. structural keyword match on channel names / detected features
  2. semantic search over the query or summary
  3. rerank top-N candidates
  4. return top-k chunks

Chroma + embeddings are wired lazily; when the index is unavailable the
retriever degrades gracefully to an empty result so the rest of the pipeline
still runs during early development.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    topic: str | None = None
    source: str | None = None
    credibility_tier: str | None = None
    score: float = 0.0


class Retriever:
    def __init__(self) -> None:
        self._collection: Any = None

    def _ensure_collection(self) -> Any | None:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            self._collection = client.get_or_create_collection("mmm_methodology")
            return self._collection
        except Exception:
            # Index not built yet (Phase 2). Degrade gracefully.
            return None

    def retrieve(
        self, query: str, top_k: int | None = None, topics: list[str] | None = None
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.rag_top_k
        collection = self._ensure_collection()
        if collection is None:
            return []

        where = {"topic": {"$in": topics}} if topics else None
        results = collection.query(
            query_texts=[query],
            n_results=settings.rag_rerank_candidates,
            where=where,
        )
        chunks = self._to_chunks(results)
        return self._rerank(query, chunks)[:top_k]

    @staticmethod
    def _to_chunks(results: dict) -> list[RetrievedChunk]:
        chunks: list[RetrievedChunk] = []
        ids = (results.get("ids") or [[]])[0]
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]
        for i, chunk_id in enumerate(ids):
            meta = metas[i] if i < len(metas) else {}
            chunks.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=docs[i] if i < len(docs) else "",
                    topic=meta.get("topic"),
                    source=meta.get("source"),
                    credibility_tier=meta.get("credibility_tier"),
                    score=1.0 - (dists[i] if i < len(dists) else 0.0),
                )
            )
        return chunks

    def _rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        """Placeholder rerank. Replace with a cross-encoder in Phase 2/3."""
        return sorted(chunks, key=lambda c: c.score, reverse=True)


retriever = Retriever()
