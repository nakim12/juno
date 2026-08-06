"""Calibration reliability analysis (design doc 9.1).

Reads the per-channel calibration points captured during a run and produces a
reliability report: for each confidence label the agent used, how often it was
actually right (within one rank of ground truth), how that compares to the
probability the ECE metric assigns that label, and what remapping would minimize
ECE. This is the diagnostic that turns "calibration is off" into an actionable
fix (adjust the prompt's confidence thresholds, or recalibrate the mapping).

Usage::

    python -m app.evaluation.calibration_report            # latest captured run
    python -m app.evaluation.calibration_report --run-id <id>
"""

from __future__ import annotations

import argparse

from app.evaluation.metrics import _CONFIDENCE_TO_PROB, expected_calibration_error
from app.evaluation.results_store import (
    calibration_points_for_run,
    latest_calibrated_run_id,
)

_LABEL_ORDER = ["high", "medium", "low"]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def reliability(run_id: str) -> dict:
    """Build the reliability report for a captured run."""
    points = calibration_points_for_run(run_id)
    if not points:
        return {"run_id": run_id, "n_points": 0}

    probs = [float(p["prob"]) for p in points]
    correct = [bool(p["correct"]) for p in points]
    total = len(points)
    overall_ece = expected_calibration_error(probs, correct)

    per_label: list[dict] = []
    suggested_map: dict[str, float] = {}
    for label in _LABEL_ORDER:
        subset = [p for p in points if p["confidence"] == label]
        if not subset:
            continue
        acc = _mean([float(p["correct"]) for p in subset])
        mapped = _CONFIDENCE_TO_PROB.get(label, 0.5)
        suggested_map[label] = round(acc, 3)
        per_label.append(
            {
                "label": label,
                "n": len(subset),
                "share": round(len(subset) / total, 3),
                "mapped_prob": mapped,
                "empirical_acc": round(acc, 3),
                "gap": round(mapped - acc, 3),  # +ve => overconfident
            }
        )

    # In-sample ECE if each label were mapped to its observed accuracy. This is a
    # floor (fit on the same data), but it bounds how much a pure remap can help.
    remapped_probs = [suggested_map.get(p["confidence"], 0.5) for p in points]
    remapped_ece = expected_calibration_error(remapped_probs, correct)

    return {
        "run_id": run_id,
        "n_points": total,
        "overall_ece": round(overall_ece, 4),
        "mean_confidence": round(_mean(probs), 4),
        "mean_accuracy": round(_mean([float(c) for c in correct]), 4),
        "per_label": per_label,
        "suggested_mapping": suggested_map,
        "remapped_ece_floor": round(remapped_ece, 4),
    }


def _direction(gap: float) -> str:
    if gap > 0.07:
        return "OVERCONFIDENT"
    if gap < -0.07:
        return "underconfident"
    return "well-calibrated"


def _recommendation(report: dict) -> list[str]:
    lines: list[str] = []
    mean_gap = report["mean_confidence"] - report["mean_accuracy"]
    if mean_gap > 0.05:
        lines.append(
            f"Overall the agent is OVERCONFIDENT (mean confidence "
            f"{report['mean_confidence']:.2f} vs. accuracy {report['mean_accuracy']:.2f}). "
            "Push it toward lower labels when credible intervals overlap."
        )
    elif mean_gap < -0.05:
        lines.append(
            f"Overall the agent is UNDER-confident (mean confidence "
            f"{report['mean_confidence']:.2f} vs. accuracy {report['mean_accuracy']:.2f}). "
            "Its ranking is more reliable than it claims — let it use 'high' more freely."
        )
    else:
        lines.append("Overall confidence tracks accuracy well.")

    for row in report["per_label"]:
        d = _direction(row["gap"])
        if d == "well-calibrated":
            continue
        lines.append(
            f"'{row['label']}' ({row['n']} channels): the agent is right "
            f"{row['empirical_acc'] * 100:.0f}% of the time but '{row['label']}' is "
            f"scored as {row['mapped_prob'] * 100:.0f}% -> {d}. "
            f"Either move some of these channels to a "
            f"{'lower' if row['gap'] > 0 else 'higher'} label, or read '{row['label']}' "
            f"as ~{row['empirical_acc'] * 100:.0f}%."
        )

    lines.append(
        "Pure remap floor: mapping labels to observed accuracy would reduce ECE to "
        f"~{report['remapped_ece_floor']:.3f} (in-sample) from {report['overall_ece']:.3f}. "
        "The durable fix is prompt thresholds so the labels mean what the metric assumes."
    )
    return lines


def _print(report: dict) -> None:
    if report.get("n_points", 0) == 0:
        print(
            f"No calibration points recorded for run {report['run_id']!r}.\n"
            "Run an eval with persistence enabled first "
            "(python -m app.evaluation.run_eval --n <N>)."
        )
        return

    print("\n" + "=" * 64)
    print(f"  Calibration reliability — run {report['run_id']}")
    print(f"  {report['n_points']} per-channel points   "
          f"overall ECE = {report['overall_ece']:.4f}")
    print("=" * 64)
    print(f"  {'Confidence':<12}{'N':>6}{'Share':>8}{'Scored':>9}{'Actual':>9}{'Gap':>8}  Verdict")
    print("  " + "-" * 62)
    for row in report["per_label"]:
        print(
            f"  {row['label']:<12}{row['n']:>6}{row['share']:>8.2f}"
            f"{row['mapped_prob']:>9.2f}{row['empirical_acc']:>9.2f}{row['gap']:>+8.2f}"
            f"  {_direction(row['gap'])}"
        )
    print("  " + "-" * 62)
    print(f"  Suggested label->prob mapping: {report['suggested_mapping']}")
    print(f"  ECE floor after remap (in-sample): {report['remapped_ece_floor']:.4f}")
    print("=" * 64)
    print("  Recommendations:")
    for line in _recommendation(report):
        print(f"   - {line}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibration reliability report.")
    parser.add_argument(
        "--run-id", default=None,
        help="run id to analyze (defaults to the most recent captured run)",
    )
    args = parser.parse_args()

    run_id = args.run_id or latest_calibrated_run_id()
    if not run_id:
        print(
            "No captured calibration data found. Run an eval with persistence first:\n"
            "  python -m app.evaluation.run_eval --n 40"
        )
        return
    _print(reliability(run_id))


if __name__ == "__main__":
    main()
