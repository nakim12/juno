"""Embedding function selection for the RAG layer (design doc 5.3).

Default is a local, free sentence-transformers model (all-MiniLM-L6-v2) served
via Chroma's built-in ONNX runtime — no API key required. Set
``EMBEDDING_BACKEND=openai`` (plus ``OPENAI_API_KEY``) to match the design doc's
text-embedding-3-small instead.

Both the indexer and the retriever import ``get_embedding_function`` so the same
embedder is used for indexing and querying (mismatched embedders return garbage).
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def get_embedding_function() -> Any:
    from chromadb.utils import embedding_functions

    if settings.embedding_backend == "openai":
        if not settings.openai_api_key:
            raise RuntimeError(
                "EMBEDDING_BACKEND=openai but OPENAI_API_KEY is not set."
            )
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name=settings.embedding_model,
        )

    # Local default: all-MiniLM-L6-v2 (384-dim), downloaded once and cached.
    return embedding_functions.DefaultEmbeddingFunction()
