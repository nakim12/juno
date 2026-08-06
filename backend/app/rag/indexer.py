"""Corpus indexing batch job (design doc 5.3).

Reads source documents from ``app/rag/corpus/``, parses per-file front-matter
metadata, chunks the body to ~500-token segments, embeds them with the same
embedding function the retriever uses, and writes to Chroma.

Front-matter format (top of each ``.md`` file):

    ---
    title: Adstock and Carryover
    topic: adstock
    source: juno_kb
    credibility_tier: synthesis
    ---
    <body text...>

Run as a module:  python -m app.rag.indexer --reset
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import settings

CORPUS_DIR = Path(__file__).parent / "corpus"
CHUNK_TARGET_TOKENS = 500


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split a leading ``--- ... ---`` YAML-ish block from the body.

    Kept dependency-free: only simple ``key: value`` lines are supported.
    """
    meta: dict[str, str] = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            block = text[3:end].strip()
            body = text[end + 4 :].lstrip("\n")
            for line in block.splitlines():
                if ":" in line:
                    key, _, value = line.partition(":")
                    meta[key.strip()] = value.strip()
            return meta, body
    return meta, text


def chunk_text(text: str, target_tokens: int = CHUNK_TARGET_TOKENS) -> list[str]:
    """Paragraph-aware chunker (~4 chars/token heuristic)."""
    approx_chars = target_tokens * 4
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    length = 0
    for para in paragraphs:
        if length + len(para) > approx_chars and current:
            chunks.append("\n\n".join(current))
            current, length = [], 0
        current.append(para)
        length += len(para) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def build_index(reset: bool = False) -> int:
    """Index every ``*.md``/``*.txt`` file under the corpus dir. Returns chunk count."""
    import chromadb

    from app.rag.embeddings import get_embedding_function

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    if reset:
        try:
            client.delete_collection("mmm_methodology")
        except Exception:
            pass
    collection = client.get_or_create_collection(
        "mmm_methodology",
        embedding_function=get_embedding_function(),
    )

    docs, ids, metadatas = [], [], []
    for path in sorted([*CORPUS_DIR.glob("*.md"), *CORPUS_DIR.glob("*.txt")]):
        if path.name.lower() == "readme.md":
            continue
        raw = path.read_text(encoding="utf-8")
        meta, body = parse_front_matter(raw)
        for i, chunk in enumerate(chunk_text(body)):
            docs.append(chunk)
            ids.append(f"{path.stem}::{i}")
            metadatas.append(
                {
                    "source": meta.get("source", path.stem),
                    "title": meta.get("title", path.stem.replace("_", " ").title()),
                    "topic": meta.get("topic", "uncategorized"),
                    "credibility_tier": meta.get("credibility_tier", "unknown"),
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
