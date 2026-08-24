"""On-disk cache of chat answers for a curated set of questions per sample.

Free-text chat is the one part of the demo with unbounded cost: every message is
a live Claude call. Rather than disable it — the multi-agent router is the most
interesting thing here — a fixed set of questions per sample is answered once,
offline, and replayed verbatim. Visitors get the full experience, including the
routed question type and the cited sources, for nothing.

Questions are matched on a normalized form so trivial differences in punctuation
or casing still hit. Anything not in the set needs the caller's own API key.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_chats"


@dataclass
class CachedAnswer:
    """One pre-computed exchange, carrying everything the UI renders live."""

    question: str
    question_type: str
    answer: str
    sources: list[dict] = field(default_factory=list)


def normalize(question: str) -> str:
    """Key form for lookups: casing, punctuation and spacing don't matter."""
    return re.sub(r"[^a-z0-9 ]", "", question.lower()).strip()


def _path(sample_id: str) -> Path:
    return _CACHE_DIR / f"{sample_id}.json"


def load(sample_id: str) -> list[CachedAnswer]:
    """Every pre-computed answer for a sample, in curated order."""
    path = _path(sample_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[CachedAnswer] = []
    for item in raw:
        try:
            out.append(
                CachedAnswer(
                    question=item["question"],
                    question_type=item.get("question_type", "interpretation"),
                    answer=item["answer"],
                    sources=item.get("sources", []),
                )
            )
        except (KeyError, TypeError):
            continue
    return out


def questions(sample_id: str) -> list[str]:
    return [a.question for a in load(sample_id)]


def find(sample_id: str, question: str) -> CachedAnswer | None:
    key = normalize(question)
    for answer in load(sample_id):
        if normalize(answer.question) == key:
            return answer
    return None


def save(sample_id: str, answers: list[CachedAnswer]) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(sample_id)
    path.write_text(
        json.dumps([asdict(a) for a in answers], indent=2), encoding="utf-8"
    )
    return path
