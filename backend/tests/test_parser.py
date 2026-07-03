from pathlib import Path

from app.models.mmm_output import MMMOutput
from app.parsers import mmm_parser

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


def _load(name: str) -> MMMOutput:
    return MMMOutput.model_validate_json((SAMPLES / f"{name}.json").read_text())


def test_parser_produces_summary():
    mmm = _load("three_channel_small_budget")
    summary = mmm_parser.parse(mmm)
    assert summary.n_channels == 3
    assert summary.ranked_channels()[0] == "Search"
    assert summary.total_spend > 0


def test_parser_flags_wide_ci_and_high_adstock():
    mmm = _load("six_channel_with_saturation")
    summary = mmm_parser.parse(mmm)
    codes = {i.code for i in summary.detected_issues}
    assert "high_adstock" in codes  # YouTube has 0.92 decay
    assert "wide_ci" in codes  # TikTok CI is wide relative to point estimate
