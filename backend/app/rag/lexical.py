"""BM25 retrieval over the methodology corpus, with no model and no vector store.

This exists because the embedding model is too big for the machine the demo runs
on. Loading ONNX MiniLM on a 512 MB container gets the process killed by the
kernel — not an exception that can be caught and degraded from, but a SIGKILL
that takes the whole service down mid-request. The only safe response is to
never load it there.

BM25 over this corpus is a smaller compromise than it sounds. There are fourteen
documents, each on one clearly named topic, and the questions that reach
retrieval say things like "what does saturation mean for budget decisions" —
the vocabulary of the query and of the right document overlap heavily. Lexical
scoring handles that well. It degrades on paraphrase, which is why the vector
backend is still preferred wherever it fits in memory.

Chunk boundaries and ids come from :mod:`app.rag.indexer`, the same code that
builds the vector index, so a citation means the same thing under either backend
and the two can be compared directly.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from app.rag.chunk import RetrievedChunk
from app.rag.indexer import CORPUS_DIR, chunk_text, parse_front_matter

# Standard BM25 parameters. k1 controls how fast term frequency saturates, b how
# strongly to normalize by document length.
K1 = 1.5
B = 0.75

# Title and topic are strong relevance signals in a corpus where each document
# covers exactly one concept, so their terms are counted this many times.
FIELD_BOOST = 3

# Weight applied to terms added by query expansion. Well below 1.0 so an
# expanded term can break a tie or rescue a query with no corpus vocabulary at
# all, but never outrank a term the user actually typed.
EXPANSION_WEIGHT = 0.4

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Terms too common in either the questions or the corpus to discriminate between
# documents. BM25's IDF already discounts them; removing them outright stops a
# long question from being scored mostly on its filler.
_STOPWORDS = frozenset(
    """
    a an and are as at be been but by can could did do does for from had has have
    he her his how i if in into is it its me my no nor not of on or our out own
    said same she should so some such than that the their them then there these
    they this those to too us was we were what when where which while who why
    will with would you your about above after again against all also am any
    because before being below between both during each few further here more
    most only other over own through under until up very
    """.split()
)


def _fold(token: str) -> str:
    """Crude singularization: "channels" -> "channel", "gross" left alone.

    A real stemmer would be another dependency for a 60 KB corpus, and the gain
    over folding a trailing "s" is small when the terms that carry the meaning
    are domain nouns like "saturation" and "adstock". It only has to be
    *consistent*, since queries and documents pass through the same function.
    """
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric terms, stopwords dropped, plurals folded."""
    return [
        _fold(token)
        for token in _TOKEN_RE.findall(text.lower())
        if token not in _STOPWORDS
    ]


# Query expansion. People ask "how much should I trust this?"; the corpus says
# "posterior credible interval". Nothing lexical can bridge that on its own, and
# it is the gap where BM25 loses most to an embedding model — so the bridge is
# written down explicitly.
#
# Entries map everyday question vocabulary onto the corpus's own terms. They are
# derived from the fourteen documents' subject matter rather than from any
# particular test query, and the held-out set in scripts/compare_retrieval.py
# exists to check that distinction held.
_RAW_EXPANSIONS: dict[str, tuple[str, ...]] = {
    # Confidence and uncertainty
    "trust": ("uncertainty", "credible", "interval", "posterior"),
    "reliable": ("uncertainty", "credible", "interval", "calibration"),
    "reliability": ("uncertainty", "credible", "interval", "calibration"),
    "confident": ("uncertainty", "credible", "interval", "posterior"),
    "confidence": ("uncertainty", "credible", "interval", "posterior"),
    "certain": ("uncertainty", "credible", "interval"),
    "sure": ("uncertainty", "credible", "interval"),
    "believe": ("uncertainty", "credible", "prior"),
    "wide": ("credible", "interval", "uncertainty", "variance"),
    "narrow": ("credible", "interval", "uncertainty"),
    "noisy": ("uncertainty", "variance", "multicollinearity"),
    # Budget decisions
    "cut": ("budget", "allocation", "marginal", "reallocation"),
    "kill": ("budget", "allocation", "marginal"),
    "stop": ("budget", "allocation", "marginal"),
    "reduce": ("budget", "allocation", "marginal", "diminishing"),
    "move": ("budget", "allocation", "reallocation", "optimization"),
    "shift": ("budget", "allocation", "reallocation", "optimization"),
    "reallocate": ("budget", "allocation", "optimization", "marginal"),
    "allocate": ("budget", "allocation", "optimization", "marginal"),
    "budget": ("allocation", "optimization", "marginal"),
    "invest": ("budget", "allocation", "marginal"),
    # Scaling spend
    "double": ("saturation", "diminishing", "marginal", "response"),
    "increase": ("saturation", "diminishing", "marginal", "response"),
    "scale": ("saturation", "diminishing", "marginal", "response"),
    "more": ("saturation", "diminishing", "marginal"),
    "spend": ("response", "marginal", "saturation"),
    "diminishing": ("saturation", "curve", "marginal"),
    # Comparison and performance
    "best": ("roi", "marginal", "comparison"),
    "better": ("roi", "marginal", "comparison"),
    "worst": ("roi", "marginal", "comparison"),
    "rank": ("roi", "marginal", "comparison"),
    "compare": ("roi", "marginal", "comparison"),
    "performance": ("roi", "marginal", "efficiency"),
    "return": ("roi", "marginal", "efficiency"),
    "efficient": ("roi", "marginal", "efficiency"),
    "headline": ("roi", "uncertainty", "summary"),
    "overview": ("roi", "uncertainty", "summary"),
    # Causality and incrementality
    "actually": ("causal", "incremental", "incrementality"),
    "really": ("causal", "incremental", "incrementality"),
    "real": ("causal", "incremental", "incrementality"),
    "true": ("causal", "incremental", "bias"),
    "cause": ("causal", "confounding", "incrementality"),
    "incremental": ("causal", "incrementality", "lift", "experiment"),
    # Validation
    "test": ("lift", "experiment", "holdout", "calibration"),
    "experiment": ("lift", "geo", "incrementality", "calibration"),
    "validate": ("holdout", "backtest", "calibration", "experiment"),
    "verify": ("holdout", "backtest", "calibration"),
    "check": ("holdout", "backtest", "calibration"),
    "accurate": ("holdout", "backtest", "calibration", "fit"),
    "overfit": ("holdout", "backtest", "fit"),
    # Structural problems
    "correlated": ("multicollinearity", "collinearity", "variance"),
    "collinear": ("multicollinearity", "collinearity", "variance"),
    "unstable": ("multicollinearity", "variance", "uncertainty"),
    "overlap": ("multicollinearity", "collinearity"),
    "wrong": ("failure", "pitfall", "bias"),
    "broken": ("failure", "pitfall", "bias"),
    "problem": ("failure", "pitfall", "bias"),
    "issue": ("failure", "pitfall", "bias"),
    "pitfall": ("failure", "bias"),
    "flag": ("failure", "pitfall", "diagnostic"),
    # Time dynamics
    "seasonal": ("seasonality", "trend", "baseline"),
    "season": ("seasonality", "trend", "baseline"),
    "holiday": ("seasonality", "trend", "baseline"),
    "trend": ("seasonality", "baseline"),
    "carryover": ("adstock", "decay", "lag"),
    "lag": ("adstock", "carryover", "decay"),
    "delayed": ("adstock", "carryover", "decay"),
    "decay": ("adstock", "carryover"),
    # Attribution
    "attribution": ("mta", "touch", "incrementality"),
    "mta": ("attribution", "touch", "incrementality"),
    "platform": ("attribution", "mta", "bias"),
    "pixel": ("attribution", "mta", "bias"),
}

# Channel names are the other systematic gap: they appear constantly in
# questions and never in a methodology corpus, so on their own they contribute
# nothing and a question like "should I cut Display?" retrieves almost at
# random. Mapping them to the generic terms the corpus does use recovers it.
_CHANNEL_WORDS = (
    "tv", "radio", "print", "search", "social", "display", "video", "audio",
    "affiliate", "email", "podcast", "influencer", "retail", "ooh", "direct",
    "tiktok", "youtube", "facebook", "instagram", "meta", "google", "bing",
    "snapchat", "pinterest", "linkedin", "twitter", "amazon", "programmatic",
    "brand", "performance", "paid", "organic",
)
_CHANNEL_TERMS = ("channel", "media", "spend", "mix")


def _build_expansions() -> dict[str, tuple[str, ...]]:
    """Fold both sides of the map so it lines up with tokenized text."""
    table: dict[str, set[str]] = {}
    for key, values in _RAW_EXPANSIONS.items():
        table.setdefault(_fold(key), set()).update(_fold(v) for v in values)
    for word in _CHANNEL_WORDS:
        table.setdefault(_fold(word), set()).update(_CHANNEL_TERMS)
    return {key: tuple(sorted(values)) for key, values in table.items()}


_EXPANSIONS = _build_expansions()


def _expand(terms: list[str]) -> list[tuple[str, float]]:
    """Query terms at full weight, plus their expansions at a reduced one."""
    weighted: list[tuple[str, float]] = [(t, 1.0) for t in terms]
    seen = set(terms)
    for term in terms:
        for extra in _EXPANSIONS.get(term, ()):
            if extra not in seen:
                seen.add(extra)
                weighted.append((extra, EXPANSION_WEIGHT))
    return weighted


@dataclass(frozen=True)
class _Doc:
    chunk_id: str
    text: str
    topic: str
    source: str
    credibility_tier: str
    tokens: tuple[str, ...]
    freqs: Counter
    length: int


@dataclass(frozen=True)
class _Index:
    docs: tuple[_Doc, ...]
    idf: dict[str, float]
    avg_len: float

    @property
    def size(self) -> int:
        return len(self.docs)


@lru_cache(maxsize=1)
def build() -> _Index:
    """Read and score the corpus once per process. Cheap: ~60 KB of markdown."""
    docs: list[_Doc] = []

    for path in sorted([*CORPUS_DIR.glob("*.md"), *CORPUS_DIR.glob("*.txt")]):
        if path.name.lower() == "readme.md":
            continue
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        title = meta.get("title", path.stem.replace("_", " ").title())
        topic = meta.get("topic", "uncategorized")

        for i, chunk in enumerate(chunk_text(body)):
            tokens = _tokenize(chunk) + _tokenize(f"{title} {topic}") * FIELD_BOOST
            docs.append(
                _Doc(
                    chunk_id=f"{path.stem}::{i}",
                    text=chunk,
                    topic=topic,
                    source=meta.get("source", path.stem),
                    credibility_tier=meta.get("credibility_tier", "unknown"),
                    tokens=tuple(tokens),
                    freqs=Counter(tokens),
                    length=len(tokens),
                )
            )

    n = len(docs)
    doc_freq = Counter(term for d in docs for term in set(d.tokens))
    # BM25's standard probabilistic IDF, floored: with only a handful of
    # documents a term in most of them can otherwise score negative and push
    # genuinely matching chunks below non-matching ones.
    idf = {
        term: max(math.log(1 + (n - df + 0.5) / (df + 0.5)), 0.01)
        for term, df in doc_freq.items()
    }
    avg_len = (sum(d.length for d in docs) / n) if n else 0.0

    return _Index(docs=tuple(docs), idf=idf, avg_len=avg_len)


def _score(doc: _Doc, query_terms: list[tuple[str, float]], index: _Index) -> float:
    score = 0.0
    for term, weight in query_terms:
        tf = doc.freqs.get(term, 0)
        if not tf:
            continue
        denom = tf + K1 * (1 - B + B * doc.length / (index.avg_len or 1))
        score += weight * index.idf.get(term, 0.0) * (tf * (K1 + 1)) / denom
    return score


def retrieve(
    query: str, top_k: int, topics: list[str] | None = None
) -> list[RetrievedChunk]:
    """Top-``top_k`` chunks for ``query``, optionally restricted to ``topics``."""
    index = build()
    if not index.size:
        return []

    terms = _tokenize(query)
    if not terms:
        return []

    candidates = [d for d in index.docs if topics is None or d.topic in topics]
    if not candidates:
        return []

    query_terms = _expand(terms)
    scored = [(d, _score(d, query_terms, index)) for d in candidates]

    # Rank everything and take top_k rather than dropping zero-scoring chunks.
    # The vector backend always returns its k nearest however weak the match is,
    # and on a fourteen-chunk corpus a question using none of the corpus's
    # vocabulary would otherwise come back with one chunk or none at all. Sort
    # by chunk_id as a tiebreak so equal scores order deterministically.
    scored.sort(key=lambda pair: (-pair[1], pair[0].chunk_id))
    top = scored[:top_k]

    # Normalize to 0..1 so callers can read `score` the same way under either
    # backend: a within-result-set ranking signal, not a calibrated probability.
    best = top[0][1] or 1.0
    return [
        RetrievedChunk(
            chunk_id=d.chunk_id,
            text=d.text,
            topic=d.topic,
            source=d.source,
            credibility_tier=d.credibility_tier,
            score=round(s / best, 4),
        )
        for d, s in top
    ]
