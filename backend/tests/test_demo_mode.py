"""The public demo must never spend the owner's API credit.

These tests pin that contract: what's free, what's refused, and what a caller's
own key unlocks.
"""

import pytest
from fastapi.testclient import TestClient

from app.core import caller_key
from app.core.caller_key import resolve_llm_access
from app.main import app

client = TestClient(app)

SAMPLE = "three_channel_small_budget"
CACHED_QUESTION = "Should I cut Display?"
CALLER_KEY = "sk-ant-caller-supplied"


@pytest.fixture
def demo_mode(monkeypatch):
    monkeypatch.setattr(caller_key.settings, "demo_mode", True)
    monkeypatch.setattr(caller_key.settings, "anthropic_api_key", "sk-ant-server-key")


def _session_id() -> str:
    resp = client.post(f"/api/samples/{SAMPLE}/load")
    assert resp.status_code == 200
    return resp.json()["session_id"]


# --- which key a request is allowed to use ---------------------------------


def test_demo_mode_withholds_the_server_key(demo_mode):
    access = resolve_llm_access(None)
    assert access.key is None
    assert not access.can_generate
    assert not access.billed_to_server


def test_caller_key_unlocks_generation_without_billing_the_server(demo_mode):
    access = resolve_llm_access(CALLER_KEY)
    assert access.key == CALLER_KEY
    assert access.can_generate
    assert not access.billed_to_server


def test_malformed_caller_key_is_ignored(demo_mode):
    """A junk header must not be forwarded to the provider as if it were a key."""
    assert resolve_llm_access("not-a-key").key is None


def test_server_key_is_used_when_demo_mode_is_off(monkeypatch):
    monkeypatch.setattr(caller_key.settings, "demo_mode", False)
    monkeypatch.setattr(caller_key.settings, "anthropic_api_key", "sk-ant-server-key")
    access = resolve_llm_access(None)
    assert access.key == "sk-ant-server-key"
    assert access.billed_to_server


# --- chat -------------------------------------------------------------------


def test_precomputed_question_is_answered_for_free(demo_mode):
    session_id = _session_id()
    resp = client.post(
        "/api/chat", json={"session_id": session_id, "message": CACHED_QUESTION}
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"cached": true' in body
    assert "event: token" in body


def test_question_matching_ignores_case_and_punctuation(demo_mode):
    session_id = _session_id()
    resp = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "should i cut display"},
    )
    assert resp.status_code == 200
    assert '"cached": true' in resp.text


def test_free_text_is_refused_without_a_key(demo_mode):
    session_id = _session_id()
    resp = client.post(
        "/api/chat",
        json={"session_id": session_id, "message": "what is the capital of France"},
    )
    assert resp.status_code == 402


def test_suggestions_describe_what_this_session_can_do(demo_mode):
    session_id = _session_id()
    body = client.get(f"/api/chat/{session_id}/suggestions").json()
    assert CACHED_QUESTION in body["questions"]
    assert body["free_text_enabled"] is False

    with_key = client.get(
        f"/api/chat/{session_id}/suggestions",
        headers={"X-Anthropic-Api-Key": CALLER_KEY},
    ).json()
    assert with_key["free_text_enabled"] is True


# --- uploads ----------------------------------------------------------------


def _sample_payload() -> dict:
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1] / "data" / "samples" / f"{SAMPLE}.json"
    )
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def test_upload_analysis_is_refused_without_a_key(demo_mode):
    resp = client.post("/api/analyze/stream", json=_sample_payload())
    assert resp.status_code == 402


def test_upload_can_still_be_parsed_for_free(demo_mode):
    """Parsing is deterministic, so the demo can offer it on any file."""
    resp = client.post("/api/parse", json=_sample_payload())
    assert resp.status_code == 200
    summary = resp.json()["summary"]
    assert summary["n_channels"] == 3
    assert "Search" in summary["channels"]


# --- the stream must survive a degraded deployment --------------------------


def test_replay_completes_without_a_vector_index(demo_mode):
    """A missing Chroma index must not truncate the analysis stream.

    Regression: retrieval raised mid-generator, which SSE delivers as a normal
    end-of-stream. The client showed a half-built report and no error at all —
    the exact symptom seen on first deploy, where the index wasn't available.
    """
    from unittest.mock import patch

    with patch(
        "app.rag.retriever.retriever.retrieve", side_effect=RuntimeError("no index")
    ):
        resp = client.post(f"/api/samples/{SAMPLE}/load/stream")

    assert resp.status_code == 200
    body = resp.text
    assert "event: report" in body, "stream ended before delivering the report"
    assert "event: done" in body
    # Citations still arrive: they're stored on the cached report, so the replay
    # never needs to query the index at all.
    assert "event: sources" in body
    assert "bayesian_priors" in body
