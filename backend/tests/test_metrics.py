from app.evaluation.metrics import (
    calibration_points,
    calibration_records,
    expected_calibration_error,
    spearman_rank_correlation,
    true_ranking_from_roi,
)
from app.models.analysis_report import (
    AnalysisReport,
    ChannelAnalysis,
    ReportMetadata,
)


def test_spearman_identical_ranking():
    ranking = ["A", "B", "C", "D"]
    assert spearman_rank_correlation(ranking, ranking) == 1.0


def test_spearman_reversed_ranking():
    assert spearman_rank_correlation(["A", "B", "C"], ["C", "B", "A"]) == -1.0


def test_ece_perfect_calibration():
    confidences = [0.0, 1.0, 1.0]
    correct = [False, True, True]
    assert expected_calibration_error(confidences, correct) == 0.0


def test_true_ranking_from_roi():
    assert true_ranking_from_roi({"A": 5.0, "B": 1.0, "C": 3.0}) == ["A", "C", "B"]


def _report(ranking: list[str], confidences: dict[str, str]) -> AnalysisReport:
    return AnalysisReport(
        session_id="t",
        overview="",
        channel_ranking=ranking,
        per_channel=[
            ChannelAnalysis(
                channel_name=name,
                interpretation="",
                confidence=conf,
                confidence_reasoning="",
            )
            for name, conf in confidences.items()
        ],
        metadata=ReportMetadata(agent_model="t", prompt_version="t", generated_at="t"),
    )


def test_calibration_scores_agent_ranking_not_model_roi():
    # Ground truth order is A > B > C. The agent ranks perfectly and is confident
    # about every channel, so every claim should be marked correct.
    true_roi = {"A": 5.0, "B": 4.0, "C": 1.0}
    report = _report(["A", "B", "C"], {"A": "high", "B": "high", "C": "high"})
    confidences, correct = calibration_points(report, true_roi)
    assert correct == [True, True, True]
    assert confidences == [0.9, 0.9, 0.9]


def test_calibration_flags_confident_but_misranked_channel():
    # Agent shoves the true-worst channel (C) to the top with high confidence.
    # C moves from true rank 2 to agent rank 0 (off by 2 > tol), so it's wrong —
    # a confident-but-incorrect claim that should hurt calibration.
    true_roi = {"A": 5.0, "B": 4.0, "C": 1.0}
    report = _report(["C", "A", "B"], {"A": "medium", "B": "medium", "C": "high"})
    _, correct = calibration_points(report, true_roi)
    by_channel = dict(zip(["A", "B", "C"], correct, strict=True))
    assert by_channel["C"] is False


def test_calibration_records_carry_ranks_and_labels():
    true_roi = {"A": 5.0, "B": 4.0, "C": 1.0}
    report = _report(["C", "A", "B"], {"A": "medium", "B": "low", "C": "high"})
    recs = {r.channel: r for r in calibration_records(report, true_roi)}
    assert recs["C"].confidence == "high"
    assert recs["C"].prob == 0.9
    assert recs["C"].agent_rank == 0 and recs["C"].true_rank == 2
    assert recs["C"].correct is False
    assert recs["A"].correct is True  # true rank 0, agent rank 1 -> within tol
    # The thin wrapper must stay consistent with the structured records.
    probs, correct = calibration_points(report, true_roi)
    assert probs == [r.prob for r in calibration_records(report, true_roi)]
    assert correct == [r.correct for r in calibration_records(report, true_roi)]
