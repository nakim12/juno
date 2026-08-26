"""RAG retrieval over the MMM methodology knowledge base (design doc 5.3).

Two backends produce the same :class:`RetrievedChunk` over the same chunk ids:

``vector``
    Chroma plus a local ONNX MiniLM embedding model. Better on paraphrase, and
    what the evaluation numbers were measured against. Costs roughly 300–400 MB
    of resident memory once the model is loaded.
``lexical``
    BM25 over the corpus, no model and no index (see :mod:`app.rag.lexical`).
    Negligible memory, and adequate on a fourteen-document corpus where each
    file covers one named concept.

The default (``auto``) picks between them by looking at the container's memory
limit. That check is not a nicety: on a 512 MB instance, loading the embedding
model gets the process OOM-killed, which SSE clients see as a normal end of
stream — a report that stops halfway with no error anywhere. A `try`/`except`
cannot help, because SIGKILL is not an exception. The only working defence is to
decide in advance not to load it.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.core.config import settings
from app.core.container import memory_limit_bytes
from app.rag.chunk import RetrievedChunk

logger = logging.getLogger(__name__)

Backend = Literal["vector", "lexical"]

# Headroom needed before the embedding model is worth attempting: the model and
# onnxruntime together account for a few hundred MB, and the rest of the app
# still has to fit. Render's free tier is 512 MB and sits well under this.
VECTOR_MIN_MEMORY_BYTES = 1_200_000_000

__all__ = ["RetrievedChunk", "Retriever", "retriever"]


class Retriever:
    def __init__(self) -> None:
        self._collection: Any = None
        self._backend: Backend | None = None

    # --- backend selection ---------------------------------------------------

    def resolve_backend(self) -> Backend:
        """Which backend to use, decided once and then remembered."""
        if self._backend is None:
            self._backend = self._choose_backend()
            logger.info("RAG retrieval backend: %s", self._backend)
        return self._backend

    @staticmethod
    def _choose_backend() -> Backend:
        configured = settings.retrieval_backend
        if configured in ("vector", "lexical"):
            return configured  # type: ignore[return-value]

        limit = memory_limit_bytes()
        if limit is not None and limit < VECTOR_MIN_MEMORY_BYTES:
            logger.warning(
                "Container memory limit is %.0f MB; using lexical retrieval "
                "because loading the embedding model here would be OOM-killed.",
                limit / 1e6,
            )
            return "lexical"
        return "vector"

    # --- vector backend ------------------------------------------------------

    def _ensure_collection(self) -> Any | None:
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            from app.rag.embeddings import get_embedding_function

            client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            self._collection = client.get_or_create_collection(
                "mmm_methodology",
                embedding_function=get_embedding_function(),
            )
            return self._collection
        except Exception:
            logger.exception("Vector index unavailable; falling back to lexical")
            return None

    # --- public API ----------------------------------------------------------

    def retrieve(
        self, query: str, top_k: int | None = None, topics: list[str] | None = None
    ) -> list[RetrievedChunk]:
        top_k = top_k or settings.rag_top_k

        if self.resolve_backend() == "lexical":
            return self._retrieve_lexical(query, top_k, topics)

        collection = self._ensure_collection()
        if collection is None:
            # The index is missing or unreadable. Lexical needs neither, so it
            # can still ground the answer rather than returning nothing.
            return self._retrieve_lexical(query, top_k, topics)

        where = {"topic": {"$in": topics}} if topics else None
        results = collection.query(
            query_texts=[query],
            n_results=settings.rag_rerank_candidates,
            where=where,
        )
        chunks = self._to_chunks(results)
        return self._rerank(query, chunks)[:top_k]

    @staticmethod
    def _retrieve_lexical(
        query: str, top_k: int, topics: list[str] | None
    ) -> list[RetrievedChunk]:
        from app.rag import lexical

        return lexical.retrieve(query, top_k, topics)

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
