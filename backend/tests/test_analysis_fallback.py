from pathlib import Path

import pytest

from app.agents import initial_analysis
from app.models.mmm_output import MMMOutput

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


@pytest.mark.asyncio
async def test_heuristic_report_without_llm_key():
    mmm = MMMOutput.model_validate_json(
        (SAMPLES / "three_channel_small_budget.json").read_text()
    )
    summary, report = await initial_analysis.run(mmm, session_id="test-session")
    assert report.session_id == "test-session"
    assert len(report.per_channel) == 3
    assert report.recommendations
    assert report.metadata.agent_model == "heuristic-fallback"
