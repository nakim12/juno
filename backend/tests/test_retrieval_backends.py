"""Retrieval must survive a container too small to hold the embedding model.

The bug these pin: on a 512 MB instance, loading ONNX MiniLM got the process
OOM-killed. Because that arrives as SIGKILL rather than an exception, the
existing try/except degradation was powerless — the service went down mid-
request and the client saw a truncated SSE stream with no error. The fix is to
decide *not* to load the model when the container is too small, so the tests
that matter are about that decision and about the backend it falls back to.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core import container
from app.core.config import settings
from app.rag import lexical
from app.rag.retriever import VECTOR_MIN_MEMORY_BYTES, Retriever

QUERY = "what does saturation mean for my budget decisions"


@pytest.fixture
def lexical_retriever() -> Retriever:
    r = Retriever()
    r._backend = "lexical"
    return r


# --- backend selection ------------------------------------------------------


def _resolve(limit: int | None, configured: str = "auto") -> str:
    with (
        patch("app.rag.retriever.memory_limit_bytes", return_value=limit),
        patch.object(settings, "retrieval_backend", configured),
    ):
        return Retriever().resolve_backend()


def test_small_container_refuses_the_embedding_model():
    """The whole point: 512 MB must not attempt a load that would be killed."""
    assert _resolve(512 * 1024 * 1024) == "lexical"


def test_generous_container_uses_the_vector_backend():
    assert _resolve(VECTOR_MIN_MEMORY_BYTES * 4) == "vector"


def test_unknown_limit_is_treated_as_unconstrained():
    """No cgroup means a normal machine; only a detected limit is a constraint."""
    assert _resolve(None) == "vector"


def test_explicit_configuration_overrides_the_memory_heuristic():
    assert _resolve(512 * 1024 * 1024, configured="vector") == "vector"
    assert _resolve(None, configured="lexical") == "lexical"


def test_backend_is_resolved_once():
    r = Retriever()
    with patch("app.rag.retriever.memory_limit_bytes", return_value=None) as probe:
        r.resolve_backend()
        r.resolve_backend()
    assert probe.call_count == 1


# --- cgroup parsing ---------------------------------------------------------


def test_cgroup_v2_max_means_unlimited(tmp_path):
    path = tmp_path / "memory.max"
    path.write_text("max")
    with patch.object(container, "_LIMIT_FILES", (path,)):
        assert container.memory_limit_bytes() is None


def test_cgroup_v1_sentinel_means_unlimited(tmp_path):
    """v1 spells "no limit" as a number near 2**63, not as an absence."""
    path = tmp_path / "memory.limit_in_bytes"
    path.write_text("9223372036854771712")
    with patch.object(container, "_LIMIT_FILES", (path,)):
        assert container.memory_limit_bytes() is None


def test_cgroup_limit_is_read(tmp_path):
    path = tmp_path / "memory.max"
    path.write_text("536870912\n")
    with patch.object(container, "_LIMIT_FILES", (path,)):
        assert container.memory_limit_bytes() == 536870912


def test_missing_cgroup_files_are_not_fatal(tmp_path):
    with patch.object(container, "_LIMIT_FILES", (tmp_path / "nope",)):
        assert container.memory_limit_bytes() is None


# --- lexical retrieval ------------------------------------------------------


def test_corpus_is_indexed():
    assert lexical.build().size >= 10


def test_returns_the_requested_number_of_chunks():
    """Parity with the vector backend, which always returns its k nearest.

    Regression: filtering to non-zero BM25 scores returned a single chunk for
    questions phrased in channel names, so answers came back near-ungrounded.
    """
    assert len(lexical.retrieve(QUERY, 8)) == 8


def test_ranks_the_obvious_document_first():
    top = lexical.retrieve("saturation curves and diminishing returns", 3)
    assert top[0].topic == "saturation"


def test_chunk_ids_match_the_vector_index_format():
    """Citations must mean the same thing under either backend."""
    ids = {c.chunk_id for c in lexical.retrieve(QUERY, 8)}
    assert all("::" in cid for cid in ids)
    assert any(cid.startswith("saturation::") for cid in ids)


def test_topic_filter_restricts_results():
    hits = lexical.retrieve(QUERY, 8, topics=["adstock"])
    assert hits and {c.topic for c in hits} == {"adstock"}


def test_scores_are_normalized_and_ordered():
    hits = lexical.retrieve(QUERY, 5)
    scores = [c.score for c in hits]
    assert scores == sorted(scores, reverse=True)
    assert scores[0] == pytest.approx(1.0)


def test_empty_query_returns_nothing():
    assert lexical.retrieve("the and of", 5) == []


def test_expansion_bridges_question_vocabulary_to_corpus_vocabulary():
    """"Trust" never appears in a methodology corpus; uncertainty does.

    This is the gap BM25 loses to an embedding model on, and the expansion
    table is what closes it.
    """
    topics = {c.topic for c in lexical.retrieve("how much should I trust this", 3)}
    assert topics & {"credible_intervals", "calibration", "bayesian_priors"}


def test_channel_names_do_not_strand_a_query():
    """Channel names appear in every question and in none of the corpus."""
    topics = {c.topic for c in lexical.retrieve("should I cut Display", 3)}
    assert topics & {"budget_optimization", "roi_mroi", "saturation"}


# --- integration through the Retriever --------------------------------------


def test_retriever_uses_lexical_without_touching_chroma(lexical_retriever):
    with patch("app.rag.retriever.Retriever._ensure_collection") as ensure:
        hits = lexical_retriever.retrieve(QUERY)
    ensure.assert_not_called()
    assert len(hits) == 8


def test_vector_backend_falls_back_when_the_index_is_missing():
    """An unreadable index should cost quality, not citations entirely."""
    r = Retriever()
    r._backend = "vector"
    with patch.object(Retriever, "_ensure_collection", return_value=None):
        hits = r.retrieve(QUERY)
    assert len(hits) == 8
