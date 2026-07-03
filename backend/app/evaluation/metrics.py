"""Aggregate evaluation metrics (design doc 5.4, 9.1).

Deterministic metrics live here; LLM-judged dimensions come from ``judge.py``.
"""

from __future__ import annotations

from dataclasses import dataclass


def spearman_rank_correlation(a: list[str], b: list[str]) -> float:
    """Spearman correlation between two rankings of the same items.

    Used for the Accuracy dimension: agent channel ranking vs. ground truth.
    Returns a value in [-1, 1]; 1.0 means identical ordering.
    """
    items = set(a) & set(b)
    if len(items) < 2:
        return 0.0
    rank_a = {name: i for i, name in enumerate(a)}
    rank_b = {name: i for i, name in enumerate(b)}
    ordered = sorted(items)
    d_squared = sum((rank_a[name] - rank_b[name]) ** 2 for name in ordered)
    n = len(ordered)
    return 1 - (6 * d_squared) / (n * (n**2 - 1))


def expected_calibration_error(
    confidences: list[float], correct: list[bool], n_bins: int = 10
) -> float:
    """Expected Calibration Error (Calibration dimension, design doc 9.1)."""
    if not confidences:
        return 0.0
    total = len(confidences)
    ece = 0.0
    for b in range(n_bins):
        lo, hi = b / n_bins, (b + 1) / n_bins
        idxs = [i for i, c in enumerate(confidences) if lo < c <= hi or (b == 0 and c == 0)]
        if not idxs:
            continue
        avg_conf = sum(confidences[i] for i in idxs) / len(idxs)
        accuracy = sum(1 for i in idxs if correct[i]) / len(idxs)
        ece += (len(idxs) / total) * abs(avg_conf - accuracy)
    return ece


@dataclass
class DimensionScores:
    accuracy: float = 0.0
    calibration: float = 0.0
    groundedness: float = 0.0
    actionability: float = 0.0
    failure_mode_recall: float = 0.0
    hallucination_rate: float = 0.0

    def weighted_total(self) -> float:
        """Weighted composite per design doc 9.1 (lower is better dims inverted)."""
        return (
            0.25 * self.accuracy
            + 0.20 * (1 - self.calibration)
            + 0.20 * self.groundedness
            + 0.15 * (self.actionability / 5.0)
            + 0.10 * self.failure_mode_recall
            + 0.10 * (1 - self.hallucination_rate)
        )
