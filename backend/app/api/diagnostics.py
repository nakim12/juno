"""Operational diagnostics for the retrieval stack.

The retriever is written to degrade quietly — an unavailable index returns no
citations rather than failing a request. That's right for visitors and wrong for
debugging: a deployment can serve traffic while silently ungrounded, and the
logs only show it once someone triggers a live query.

This endpoint deliberately does the opposite. It exercises each layer in order
and reports exactly where and how it breaks, so a broken index is a URL you can
check rather than an inference from missing citations.

It exposes paths and exception messages, not data or secrets.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["meta"])


def _err(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


@router.get("/rag")
def rag_health() -> dict[str, Any]:
    """Walk the retrieval stack layer by layer, reporting the first failure."""
    out: dict[str, Any] = {
        "embedding_backend": settings.embedding_backend,
        "persist_dir": settings.chroma_persist_dir,
    }

    # 1. Is the persisted index even on disk? Distinguishes "build didn't run"
    #    from "build ran but runtime can't use it".
    path = Path(settings.chroma_persist_dir)
    out["persist_dir_exists"] = path.exists()
    if path.exists():
        try:
            entries = list(path.rglob("*"))
            out["persist_files"] = len([e for e in entries if e.is_file()])
            out["persist_bytes"] = sum(e.stat().st_size for e in entries if e.is_file())
        except Exception as exc:
            out["persist_scan_error"] = _err(exc)

    # 2. Can the embedding function be constructed? For the local backend this
    #    is where the ONNX model is resolved, and where a cold container that
    #    can't fetch it will fail.
    try:
        from app.rag.embeddings import get_embedding_function

        embed = get_embedding_function()
        out["embedding_function"] = type(embed).__name__
    except Exception as exc:
        out["embedding_function_error"] = _err(exc)
        return out

    # 3. Can it actually embed? Constructing is lazy; this forces the model to
    #    load and is the step that fails at runtime while the build succeeded.
    try:
        vec = embed(["saturation curve"])
        out["embed_ok"] = True
        out["embed_dim"] = len(vec[0]) if vec else 0
    except Exception as exc:
        out["embed_ok"] = False
        out["embed_error"] = _err(exc)

    # 4. Does the collection open, and does it hold the corpus?
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

    # 5. The real thing, end to end.
    try:
        from app.rag.retriever import retriever

        chunks = retriever.retrieve("what does saturation mean for budget decisions")
        out["retrieve_ok"] = True
        out["retrieved"] = len(chunks)
        out["sample_chunk_ids"] = [c.chunk_id for c in chunks[:3]]
    except Exception as exc:
        out["retrieve_ok"] = False
        out["retrieve_error"] = _err(exc)

    return out
