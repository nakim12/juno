"""The unit of retrieval, shared by every backend.

Lives in its own module so the vector and lexical retrievers can both produce it
without importing each other.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    topic: str | None = None
    source: str | None = None
    credibility_tier: str | None = None
    # Relevance in 0..1, comparable within one result set but not across
    # backends: the vector path derives it from cosine distance, the lexical
    # path from a normalized BM25 score.
    score: float = 0.0
