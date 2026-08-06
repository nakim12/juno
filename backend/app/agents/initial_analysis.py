"""Initial analysis pipeline (design doc 5.1).

Stages:
  1. Parse       -> MMMSummary (deterministic, in app.parsers)
  2. Retrieve    -> knowledge base context (app.rag)
  3. Analyze     -> AnalysisReport via the analysis agent (LLM, structured)
  4. Cache       -> stored on the session by the API layer

If no LLM key is configured, ``_heuristic_report`` produces a deterministic
report so the end-to-end skeleton is demoable before wiring the API key.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from app.agents import prompts
from app.core.llm import LLMClient, LLMNotConfigured, get_agent_llm
from app.models.analysis_report import (
    AnalysisReport,
    ChannelAnalysis,
    Citation,
    KnowledgeSource,
    Recommendation,
    ReportMetadata,
    Risk,
    ValidationStep,
)
from app.models.mmm_summary import MMMSummary
from app.parsers import mmm_parser
from app.rag.retriever import retriever

PROMPT_NAME = "analysis"

# Upper bound on the analysis report generation. Large multi-channel scenarios
# (up to 10 channels, each with analysis + citations) can exceed a smaller cap
# and truncate the JSON mid-token, so give the model ample room.
MAX_ANALYSIS_TOKENS = 16000


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _retrieval_query(summary: MMMSummary) -> str:
    channels = ", ".join(c.name for c in summary.channels)
    issues = ", ".join(i.code for i in summary.detected_issues)
    return (
        f"{summary.model_type} MMM with channels: {channels}. "
        f"Detected features: {issues or 'none'}."
    )


def _knowledge_sources(chunks) -> list[KnowledgeSource]:
    """Build the grounding list from retrieved chunks (populated by the pipeline)."""
    return [
        KnowledgeSource(
            chunk_id=c.chunk_id,
            topic=c.topic,
            source=c.source,
            snippet=(c.text[:220] + "…") if len(c.text) > 220 else c.text,
        )
        for c in chunks
    ]


async def run(
    mmm_output, session_id: str, llm: LLMClient | None = None
) -> tuple[MMMSummary, AnalysisReport]:
    summary = mmm_parser.parse(mmm_output)
    chunks = retriever.retrieve(_retrieval_query(summary))

    llm = llm or get_agent_llm()
    try:
        system, user = _build_prompt(summary, chunks)
        raw = await llm.structured(
            system, user, AnalysisReport, max_tokens=MAX_ANALYSIS_TOKENS
        )
        report = _finalize_report(raw, session_id, llm)
    except LLMNotConfigured:
        report = _heuristic_report(summary, session_id)
    _ensure_ranking(report, summary)
    report.knowledge_sources = _knowledge_sources(chunks)
    return summary, report


async def run_streaming(
    mmm_output, session_id: str, llm: LLMClient | None = None
) -> AsyncIterator[tuple[str, Any]]:
    """Run the pipeline while yielding progress events for SSE.

    Yields ``(kind, payload)`` tuples where ``kind`` is one of:
      * ``"summary"``  -> the parsed :class:`MMMSummary`
      * ``"sources"``  -> list of :class:`KnowledgeSource` grounding the report
      * ``"token"``    -> a chunk of the model's raw generation (progress only)
      * ``"report"``   -> the final validated :class:`AnalysisReport`

    The caller is responsible for persisting the summary and report on the
    session and for translating events into the wire format.
    """
    summary = mmm_parser.parse(mmm_output)
    yield "summary", summary

    chunks = retriever.retrieve(_retrieval_query(summary))
    sources = _knowledge_sources(chunks)
    yield "sources", sources

    llm = llm or get_agent_llm()
    try:
        system, user = _build_prompt(summary, chunks)
        buffer: list[str] = []
        async for text in llm.structured_stream(
            system, user, AnalysisReport, max_tokens=MAX_ANALYSIS_TOKENS
        ):
            buffer.append(text)
            yield "token", text
        raw = LLMClient._parse_json("".join(buffer), AnalysisReport)
        report = _finalize_report(raw, session_id, llm)
    except LLMNotConfigured:
        report = _heuristic_report(summary, session_id)

    _ensure_ranking(report, summary)
    report.knowledge_sources = sources
    yield "report", report


def _build_prompt(summary, chunks) -> tuple[str, str]:
    system = prompts.load(PROMPT_NAME)
    kb = "\n\n".join(f"[{c.chunk_id}] {c.text}" for c in chunks) or "(none retrieved)"
    available_ids = ", ".join(c.chunk_id for c in chunks)
    user = (
        f"MMM_OUTPUT (parsed summary):\n{summary.model_dump_json(indent=2)}\n\n"
        f"KNOWLEDGE_BASE:\n{kb}\n\n"
        f"AVAILABLE_KB_CITATION_IDS: [{available_ids}]\n"
        "Reminder: every structural_risk and every recommendation must include at "
        "least one knowledge_base citation from the ids above whenever the topic "
        "(saturation, adstock, uncertainty, multicollinearity, calibration, "
        "ROI/marginal ROI, seasonality, budget allocation) is covered. Cite the "
        "exact id, e.g. {\"source_type\": \"knowledge_base\", \"reference\": "
        "\"calibration::0\"}."
    )
    return system, user


def _finalize_report(report: AnalysisReport, session_id: str, llm) -> AnalysisReport:
    report.session_id = session_id
    report.metadata = ReportMetadata(
        agent_model=llm._model,
        prompt_version=prompts.version_tag(PROMPT_NAME),
        generated_at=_now(),
    )
    return report


def _ensure_ranking(report: AnalysisReport, summary: MMMSummary) -> None:
    """Guarantee a complete, valid channel ranking.

    The agent is asked to supply ``channel_ranking`` (its own judgment). If it is
    missing, incomplete, or contains unknown names, fall back to (and complete
    with) the ROI-point ordering so downstream accuracy/calibration always have a
    well-formed ranking over exactly the model's channels.
    """
    valid = [c.name for c in summary.channels]
    valid_set = set(valid)
    ranked = [name for name in report.channel_ranking if name in valid_set]
    seen = set(ranked)
    # Append any channels the agent omitted, in ROI-point order, so the ranking
    # covers every channel exactly once.
    for name in summary.ranked_channels():
        if name not in seen:
            ranked.append(name)
            seen.add(name)
    report.channel_ranking = ranked


def _heuristic_report(summary: MMMSummary, session_id: str) -> AnalysisReport:
    """Deterministic fallback report used when no LLM key is configured."""
    ranked = summary.ranked_channels()
    per_channel = [
        ChannelAnalysis(
            channel_name=c.name,
            interpretation=(
                f"{c.name} shows an estimated ROI of {c.roi_point:.2f} "
                f"(95% CI {c.roi_ci[0]:.2f}-{c.roi_ci[1]:.2f}) and contributes "
                f"{c.contribution_pct * 100:.1f}% of attributed outcome."
            ),
            confidence="low" if c.ci_width >= c.roi_point else "medium",
            confidence_reasoning=(
                "Wide credible interval relative to the point estimate."
                if c.ci_width >= c.roi_point
                else "Interval is reasonably tight relative to the estimate."
            ),
            citations=[Citation(source_type="mmm_output", reference=c.name)],
        )
        for c in summary.channels
    ]
    risks = [
        Risk(
            title=f"{issue.code} ({issue.channel})" if issue.channel else issue.code,
            description=issue.detail,
            severity="medium",
            citations=[
                Citation(source_type="mmm_output", reference=issue.channel or "model")
            ],
        )
        for issue in summary.detected_issues
    ]
    top = ranked[0] if ranked else "the top channel"
    recommendations = [
        Recommendation(
            action=f"Prioritize incremental budget toward {top} pending saturation checks.",
            priority="high",
            rationale="Highest ROI point estimate among modeled channels.",
            confidence="medium",
            dependencies=["Confirm the channel is not near saturation."],
            citations=[Citation(source_type="mmm_output", reference=top)],
        )
    ]
    validation = [
        ValidationStep(
            step="Run a geo lift test on the top-ranked channel.",
            rationale="Validate the model's ROI estimate against a causal benchmark.",
        )
    ]
    return AnalysisReport(
        session_id=session_id,
        overview=(
            f"This {summary.model_type} model covers {summary.n_channels} channels over "
            f"{summary.data_span_weeks or 'an unspecified number of'} weeks. "
            f"By ROI point estimate, channels rank: {', '.join(ranked)}. "
            "NOTE: generated by the deterministic fallback (no LLM key configured)."
        ),
        channel_ranking=ranked,
        per_channel=per_channel,
        structural_risks=risks,
        recommendations=recommendations,
        validation_suggestions=validation,
        metadata=ReportMetadata(
            agent_model="heuristic-fallback",
            prompt_version="none",
            generated_at=_now(),
        ),
    )
