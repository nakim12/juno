from app.core.config import settings
from app.evaluation import results_store
from app.evaluation.calibration_report import reliability
from app.evaluation.results_store import (
    CalibrationPoint,
    calibration_points_for_run,
    latest_calibrated_run_id,
    save_calibration_points,
)


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "eval_db_path", str(tmp_path / "eval.db"))


def _point(run_id, ch, conf, prob, correct, ar, tr):
    return CalibrationPoint(
        run_id=run_id, case_id="c0", channel=ch, confidence=conf,
        prob=prob, correct=correct, agent_rank=ar, true_rank=tr,
    )


def test_calibration_points_round_trip(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    pts = [
        _point("run1", "A", "high", 0.9, True, 0, 0),
        _point("run1", "B", "medium", 0.6, False, 1, 3),
    ]
    assert save_calibration_points(pts) == 2
    rows = calibration_points_for_run("run1")
    assert len(rows) == 2
    assert {r["channel"] for r in rows} == {"A", "B"}
    assert latest_calibrated_run_id() == "run1"


def test_reliability_flags_underconfidence(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    # 10 'medium' channels the agent actually gets right 9/10 times -> underconfident.
    pts = [_point("r", f"m{i}", "medium", 0.6, i < 9, 0, 0) for i in range(10)]
    save_calibration_points(pts)

    report = reliability("r")
    assert report["n_points"] == 10
    row = next(r for r in report["per_label"] if r["label"] == "medium")
    assert row["empirical_acc"] == 0.9
    assert row["gap"] < 0  # scored 0.6 but right 0.9 -> underconfident
    # Remapping medium->0.9 should drive in-sample ECE toward zero.
    assert report["suggested_mapping"]["medium"] == 0.9
    assert report["remapped_ece_floor"] < report["overall_ece"]


def test_reliability_empty_run(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    assert reliability("nope") == {"run_id": "nope", "n_points": 0}
    # touch results_store to keep import used and DB path applied
    assert results_store.latest_calibrated_run_id() is None
