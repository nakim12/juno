from fastapi.testclient import TestClient

from app.api import evaluation as eval_api
from app.main import app

client = TestClient(app)

DIMENSIONS = {
    "accuracy",
    "calibration_ece",
    "groundedness",
    "actionability",
    "failure_mode_recall",
    "hallucination_rate",
}


def test_summary_always_returns_targets():
    resp = client.get("/api/evaluation/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert DIMENSIONS.issubset(data["targets"].keys())
    for meta in data["targets"].values():
        assert {"label", "target", "direction"} <= meta.keys()
        assert meta["direction"] in {"higher", "lower"}


def test_snapshot_fallback_when_db_empty(monkeypatch):
    # Simulate a fresh deployment: no benchmark rows on the server. The endpoint
    # should still serve the committed snapshot so the Trust page has real numbers.
    monkeypatch.setattr(eval_api, "all_runs", lambda: [])
    monkeypatch.setattr(eval_api, "all_failures", lambda: [])

    resp = client.get("/api/evaluation/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["available"] is True
    assert "run" in data and "judge_validation" in data
    run = data["run"]
    for key in DIMENSIONS:
        assert key in run


def test_db_summary_merges_judge_validation(monkeypatch):
    # When live DB rows exist, the endpoint uses them but still merges the
    # judge-validation block (which isn't persisted in the DB) from the snapshot.
    fake_run = {
        "run_id": "test",
        "created_at": "2026-01-01T00:00:00+00:00",
        "n_cases": 2,
        "agent_model": "claude-sonnet-4-5",
        "judge_model": "claude-opus-4-5",
        "prompt_version": "analysis.v2",
        "accuracy": 0.9,
        "calibration_ece": 0.05,
        "groundedness": 0.95,
        "actionability": 4.2,
        "failure_mode_recall": 0.8,
        "hallucination_rate": 0.02,
        "weighted_total": 0.88,
        "scenario_breakdown": '{"recall_by_failure_mode": {"wide_ci": 1.0}}',
    }
    monkeypatch.setattr(eval_api, "all_runs", lambda: [fake_run])
    monkeypatch.setattr(eval_api, "all_failures", lambda: [])

    data = client.get("/api/evaluation/summary").json()
    assert data["available"] is True
    assert data["run"]["run_id"] == "test"
    # scenario_breakdown is parsed from its JSON string into a dict.
    assert data["run"]["scenario_breakdown"]["recall_by_failure_mode"]["wide_ci"] == 1.0
    assert "judge_validation" in data
