from pathlib import Path

import pytest

from app.agents import initial_analysis
from app.core.llm import LLMClient
from app.models.mmm_output import MMMOutput

SAMPLES = Path(__file__).resolve().parents[1] / "data" / "samples"


@pytest.mark.asyncio
async def test_heuristic_report_without_llm_key():
    mmm = MMMOutput.model_validate_json(
        (SAMPLES / "three_channel_small_budget.json").read_text()
    )
    # An explicitly-unconfigured client (empty key) forces the LLMNotConfigured
    # fallback path deterministically, regardless of any ANTHROPIC_API_KEY in the
    # environment — so the test asserts the heuristic report, not a live call.
    unconfigured = LLMClient(api_key="")
    summary, report = await initial_analysis.run(
        mmm, session_id="test-session", llm=unconfigured
    )
    assert report.session_id == "test-session"
    assert len(report.per_channel) == 3
    assert report.recommendations
    assert report.metadata.agent_model == "heuristic-fallback"
    # The ranking must be complete: every channel exactly once.
    channel_names = {c.name for c in summary.channels}
    assert set(report.channel_ranking) == channel_names
    assert len(report.channel_ranking) == len(channel_names)
