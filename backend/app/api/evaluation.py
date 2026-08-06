"""Evaluation summary endpoint (design doc 5.4).

Surfaces the latest benchmark run's metrics, the failure-mode summary, and the
judge-validation (reliability) result to the product's "Trust & Evaluation"
page. Reads live from the eval DB when available and falls back to a committed
JSON snapshot so the page still shows real numbers in a fresh deployment where
no benchmark has been run on the server.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from fastapi import APIRouter

from app.evaluation.failure_catalog import all_failures
from app.evaluation.results_store import all_runs

router = APIRouter(prefix="/api/evaluation", tags=["evaluation"])

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "snapshot.json"

TARGETS = {
    "accuracy": {"label": "Accuracy (Spearman)", "target": "> 0.85", "direction": "higher"},
    "calibration_ece": {"label": "Calibration (ECE)", "target": "< 0.10", "direction": "lower"},
    "groundedness": {"label": "Groundedness", "target": "> 0.90", "direction": "higher"},
    "actionability": {"label": "Actionability (/5)", "target": "> 4.0", "direction": "higher"},
    "failure_mode_recall": {"label": "Failure recall", "target": "> 0.75", "direction": "higher"},
    "hallucination_rate": {"label": "Hallucination", "target": "< 0.05", "direction": "lower"},
}


def _load_snapshot() -> dict | None:
    if SNAPSHOT_PATH.exists():
        try:
            return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
    return None


def _summary_from_db() -> dict | None:
    runs = all_runs()
    if not runs:
        return None
    latest = dict(runs[-1])
    try:
        latest["scenario_breakdown"] = json.loads(latest.get("scenario_breakdown") or "{}")
    except (TypeError, json.JSONDecodeError):
        latest["scenario_breakdown"] = {}
    fails = all_failures()
    by_cat = dict(Counter(f["category"] for f in fails if f["category"]))
    return {
        "available": True,
        "run": latest,
        "failures": {"total": len(fails), "by_category": by_cat},
    }


@router.get("/summary")
def summary() -> dict:
    """Latest eval metrics + failure summary + judge-validation, with fallback."""
    data = _summary_from_db()
    snapshot = _load_snapshot()

    if data is None:
        # No live DB rows — serve the committed snapshot (e.g. in production).
        data = snapshot or {"available": False}
    elif snapshot and "judge_validation" in snapshot:
        # Reliability isn't stored in the DB; merge it from the snapshot.
        data.setdefault("judge_validation", snapshot["judge_validation"])

    data["targets"] = TARGETS
    return data
