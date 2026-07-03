"""Corpus indexing batch job (design doc 5.3).

Reads source documents from ``app/rag/corpus/``, chunks them to ~500-token
segments with metadata tags, embeds them, and writes to Chroma.

Run as a module:  python -m app.rag.indexer
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings

CORPUS_DIR = Path(__file__).parent / "corpus"
CHUNK_TARGET_TOKENS = 500


def chunk_text(text: str, target_tokens: int = CHUNK_TARGET_TOKENS) -> list[str]:
    """Naive whitespace chunker (~4 chars/token heuristic).

    Replace with a sentence-aware splitter (e.g. from `langchain-text-splitters`)
    once the corpus is finalized.
    """
    approx_chars = target_tokens * 4
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        current.append(word)
        length += len(word) + 1
        if length >= approx_chars:
            chunks.append(" ".join(current))
            current, length = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_index(reset: bool = False) -> int:
    """Index every ``*.md``/``*.txt`` file under the corpus dir. Returns chunk count."""
    import chromadb

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    if reset:
        try:
            client.delete_collection("mmm_methodology")
        except Exception:
            pass
    collection = client.get_or_create_collection("mmm_methodology")

    docs, ids, metadatas = [], [], []
    for path in sorted([*CORPUS_DIR.glob("*.md"), *CORPUS_DIR.glob("*.txt")]):
        text = path.read_text(encoding="utf-8")
        for i, chunk in enumerate(chunk_text(text)):
            docs.append(chunk)
            ids.append(f"{path.stem}::{i}")
            metadatas.append(
                {
                    "source": path.stem,
                    "topic": "uncategorized",
                    "credibility_tier": "unknown",
                }
            )

    if docs:
        collection.upsert(documents=docs, ids=ids, metadatas=metadatas)
    return len(docs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index the MMM methodology corpus.")
    parser.add_argument("--reset", action="store_true", help="Drop the collection first.")
    args = parser.parse_args()
    count = build_index(reset=args.reset)
    print(f"Indexed {count} chunks into '{settings.chroma_persist_dir}'.")
