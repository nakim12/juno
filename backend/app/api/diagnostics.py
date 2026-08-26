"""Operational diagnostics for the retrieval stack.

The retriever degrades quietly by design — an unavailable index costs citations,
not availability. That's right for visitors and useless for debugging, since a
deployment can serve traffic while silently ungrounded and only reveal it to
whoever notices the missing sources. This endpoint reports what the retriever
would rather hide.

The default response is cheap and safe: configuration, the resolved backend, the
memory limit that decided it, and a real lexical query. Anything that loads the
embedding model is behind ``?probe=vector``, because on a small container that
load is fatal — the first version of this endpoint took the service down every
time it was called, which is precisely the bug it was written to find.

It exposes paths, sizes and exception messages. No secrets, no user data.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from app.core.config import settings
from app.core.container import memory_limit_bytes
from app.rag.retriever import VECTOR_MIN_MEMORY_BYTES, retriever

router = APIRouter(prefix="/health", tags=["meta"])


def _err(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


@router.get("/rag")
def rag_health(
    probe: str = Query(
        default="safe",
        pattern="^(safe|vector)$",
        description=(
            "'safe' (default) avoids loading the embedding model. 'vector' "
            "forces it, which will be OOM-killed on a small container."
        ),
    ),
) -> dict[str, Any]:
    """Report retrieval health without breaking it."""
    limit = memory_limit_bytes()
    out: dict[str, Any] = {
        "configured_backend": settings.retrieval_backend,
        "resolved_backend": retriever.resolve_backend(),
        "memory_limit_mb": round(limit / 1e6, 1) if limit else None,
        "vector_needs_mb": round(VECTOR_MIN_MEMORY_BYTES / 1e6, 1),
        "embedding_backend": settings.embedding_backend,
        "persist_dir": settings.chroma_persist_dir,
    }

    # Is the persisted index on disk at all? Separates "the build never indexed"
    # from "the build indexed but the runtime can't use it".
    path = Path(settings.chroma_persist_dir)
    out["persist_dir_exists"] = path.exists()
    if path.exists():
        try:
            files = [e for e in path.rglob("*") if e.is_file()]
            out["persist_files"] = len(files)
            out["persist_bytes"] = sum(e.stat().st_size for e in files)
        except Exception as exc:
            out["persist_scan_error"] = _err(exc)

    # The lexical index needs no model, so it is always safe to exercise fully.
    try:
        from app.rag import lexical

        index = lexical.build()
        out["lexical_chunks"] = index.size
        hits = lexical.retrieve("what does saturation mean for budget decisions", 3)
        out["lexical_top_hits"] = [c.chunk_id for c in hits]
    except Exception as exc:
        out["lexical_error"] = _err(exc)

    if probe != "vector":
        out["note"] = "Pass ?probe=vector to load the embedding model."
        return out

    # --- opt-in, and genuinely dangerous on a constrained host ---------------
    out["probe"] = "vector"
    try:
        from app.rag.embeddings import get_embedding_function

        embed = get_embedding_function()
        out["embedding_function"] = type(embed).__name__
        vector = embed(["saturation curve"])
        out["embed_ok"] = True
        out["embed_dim"] = len(vector[0]) if vector else 0
    except Exception as exc:
        out["embed_ok"] = False
        out["embed_error"] = _err(exc)
        return out

    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        collection = client.get_or_create_collection(
            "mmm_methodology", embedding_function=embed
        )
        out["collection_count"] = collection.count()
    except Exception as exc:
        out["collection_error"] = _err(exc)

    return out
