from app.evaluation.metrics import expected_calibration_error, spearman_rank_correlation


def test_spearman_identical_ranking():
    ranking = ["A", "B", "C", "D"]
    assert spearman_rank_correlation(ranking, ranking) == 1.0


def test_spearman_reversed_ranking():
    assert spearman_rank_correlation(["A", "B", "C"], ["C", "B", "A"]) == -1.0


def test_ece_perfect_calibration():
    confidences = [0.0, 1.0, 1.0]
    correct = [False, True, True]
    assert expected_calibration_error(confidences, correct) == 0.0
