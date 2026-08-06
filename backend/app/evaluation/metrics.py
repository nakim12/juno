"""Aggregate evaluation metrics (design doc 5.4, 9.1).

Deterministic metrics live here; LLM-judged dimensions come from ``judge.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.analysis_report import AnalysisReport
from app.models.mmm_summary import MMMSummary

_CONFIDENCE_TO_PROB = {"high": 0.9, "medium": 0.6, "low": 0.3}

# Maps a known ground-truth failure tag to keywords that indicate the agent
# flagged it in a structural risk (for tags the parser cannot detect directly).
_FAILURE_KEYWORDS = {
    "multicollinearity": ("multicollinear", "collinear", "correlated spend", "correlated channel"),
    "saturation_extrapolation": ("saturat", "extrapolat", "diminishing return"),
}


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


def cohens_kappa(a: list[int], b: list[int], weighted: bool = True, max_score: int = 5) -> float:
    """Cohen's kappa between two raters' ordinal scores (design doc 9.2).

    Uses quadratic weighting by default, which is appropriate for ordinal 0-5
    scores (disagreeing by 1 is penalized far less than disagreeing by 4).
    Returns 1.0 for perfect agreement, 0.0 for chance-level, negative for worse
    than chance. Returns 0.0 when there is no variance to assess.
    """
    if not a or len(a) != len(b):
        return 0.0
    categories = list(range(max_score + 1))
    n = len(a)

    def weight(i: int, j: int) -> float:
        if not weighted:
            return 0.0 if i == j else 1.0
        return ((i - j) ** 2) / (max_score**2)

    # Observed and expected weighted disagreement.
    count_a = {c: a.count(c) for c in categories}
    count_b = {c: b.count(c) for c in categories}
    observed = sum(weight(a[k], b[k]) for k in range(n)) / n
    expected = sum(
        weight(i, j) * (count_a[i] / n) * (count_b[j] / n)
        for i in categories
        for j in categories
    )
    if expected == 0:
        return 1.0 if observed == 0 else 0.0
    return 1.0 - observed / expected


def agreement_report(a: list[int], b: list[int], max_score: int = 5) -> dict[str, float]:
    """Summary agreement stats between two raters over the same items."""
    if not a or len(a) != len(b):
        return {"n": 0, "exact_match": 0.0, "within_one": 0.0, "kappa": 0.0, "mean_abs_error": 0.0}
    n = len(a)
    exact = sum(1 for x, y in zip(a, b, strict=False) if x == y) / n
    within_one = sum(1 for x, y in zip(a, b, strict=False) if abs(x - y) <= 1) / n
    mae = sum(abs(x - y) for x, y in zip(a, b, strict=False)) / n
    return {
        "n": n,
        "exact_match": round(exact, 4),
        "within_one": round(within_one, 4),
        "kappa": round(cohens_kappa(a, b, weighted=True, max_score=max_score), 4),
        "mean_abs_error": round(mae, 4),
    }


def detected_failure_modes(summary: MMMSummary, report: AnalysisReport) -> set[str]:
    """Failure-mode tags the agent surfaced (parser issues + flagged risks).

    Parser-detectable tags (``wide_ci``, ``high_adstock``, ``low_contribution``)
    come from the deterministic summary. Higher-level tags
    (``multicollinearity``, ``saturation_extrapolation``) are matched against the
    text of the report's structural risks and overview.
    """
    detected: set[str] = {issue.code for issue in summary.detected_issues}

    risk_text = " ".join(
        f"{r.title} {r.description}" for r in report.structural_risks
    ).lower()
    risk_text += " " + (report.overview or "").lower()
    for tag, keywords in _FAILURE_KEYWORDS.items():
        if any(kw in risk_text for kw in keywords):
            detected.add(tag)
    return detected


def failure_mode_recall(known: list[str], detected: set[str]) -> float | None:
    """Recall on tagged failure modes for a single case.

    Returns ``None`` when the case has no known failure modes (so it can be
    excluded from the aggregate rather than counted as a perfect/zero score).
    """
    if not known:
        return None
    hits = sum(1 for tag in known if tag in detected)
    return hits / len(known)


def true_ranking_from_roi(true_roi: dict[str, float]) -> list[str]:
    """Channel names ordered by true ROI, descending (ground-truth ranking)."""
    return [name for name, _ in sorted(true_roi.items(), key=lambda kv: kv[1], reverse=True)]


@dataclass
class CalibrationRecord:
    """One per-channel calibration observation (feeds ECE and the reliability report)."""

    channel: str
    confidence: str
    prob: float
    correct: bool
    agent_rank: int
    true_rank: int


def calibration_records(
    report: AnalysisReport, true_roi: dict[str, float], tol_positions: int = 1
) -> list[CalibrationRecord]:
    """Per-channel calibration observations for a single case.

    This scores the *agent's own judgment*, not the underlying model's numbers.
    For each channel the agent states a confidence; ``correct`` means the agent
    placed that channel within ``tol_positions`` of its true rank in the agent's
    own ``channel_ranking``. A well-calibrated agent should be confident about
    channels it ranks correctly and less confident about the ones it misplaces.
    """
    if not report.channel_ranking or not true_roi:
        return []
    true_rank = {name: i for i, name in enumerate(true_ranking_from_roi(true_roi))}
    agent_rank = {name: i for i, name in enumerate(report.channel_ranking)}
    records: list[CalibrationRecord] = []
    for ch in report.per_channel:
        name = ch.channel_name
        if name not in true_rank or name not in agent_rank:
            continue
        records.append(
            CalibrationRecord(
                channel=name,
                confidence=ch.confidence,
                prob=_CONFIDENCE_TO_PROB.get(ch.confidence, 0.5),
                correct=abs(agent_rank[name] - true_rank[name]) <= tol_positions,
                agent_rank=agent_rank[name],
                true_rank=true_rank[name],
            )
        )
    return records


def calibration_points(
    report: AnalysisReport, true_roi: dict[str, float], tol_positions: int = 1
) -> tuple[list[float], list[bool]]:
    """(confidence, correct) pairs feeding Expected Calibration Error.

    Thin wrapper over :func:`calibration_records` for callers that only need the
    two parallel lists.
    """
    recs = calibration_records(report, true_roi, tol_positions)
    return [r.prob for r in recs], [r.correct for r in recs]


def material_hallucination_rate(scores: list[int], floor: int = 3) -> float:
    """Fraction of judged responses that contain a *material* hallucination.

    A response "hallucinates" when its judge hallucination score falls below
    ``floor`` — i.e. it invents a number, channel, or claim absent from the
    input (see the judge rubric). This is a true response-level rate, unlike the
    earlier ``1 - mean_score/5`` which conflated ordinary imperfection (a 4/5)
    with fabrication. Returns 0.0 when there are no judged responses.
    """
    if not scores:
        return 0.0
    return sum(1 for s in scores if s < floor) / len(scores)


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
