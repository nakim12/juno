"""Output schema for the initial analysis pipeline (design doc 5.1 / 5.7)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Confidence = Literal["high", "medium", "low"]
Priority = Literal["high", "medium", "low"]

_VALID_SOURCE_TYPES = {"mmm_output", "knowledge_base"}


class Citation(BaseModel):
    """A grounding pointer to either the MMM output or a knowledge base chunk."""

    source_type: Literal["mmm_output", "knowledge_base"]
    reference: str = Field(..., description="Channel/field name, or KB chunk id.")
    snippet: str | None = None


def _sanitize_citations(value: Any) -> Any:
    """Salvage or drop malformed citations before strict validation.

    The LLM occasionally emits citations like
    ``{"source_type": "calibration::0"}`` — putting a KB chunk id in
    ``source_type`` and omitting ``reference``. Rather than failing the whole
    report, remap those to a proper ``knowledge_base`` citation and drop anything
    that still can't form a valid citation. Well-formed citations pass through
    untouched.
    """
    if not isinstance(value, list):
        return value
    cleaned: list[Any] = []
    for item in value:
        if not isinstance(item, dict):
            cleaned.append(item)  # let Citation/Pydantic handle non-dicts
            continue
        source_type = item.get("source_type")
        reference = item.get("reference")
        if source_type in _VALID_SOURCE_TYPES and reference:
            cleaned.append(item)
        elif isinstance(source_type, str) and "::" in source_type and not reference:
            # A KB chunk id landed in source_type; remap to a valid citation.
            cleaned.append(
                {
                    "source_type": "knowledge_base",
                    "reference": source_type,
                    "snippet": item.get("snippet"),
                }
            )
        # otherwise: unsalvageable, drop it
    return cleaned


class ChannelAnalysis(BaseModel):
    channel_name: str
    interpretation: str
    confidence: Confidence
    confidence_reasoning: str
    citations: list[Citation] = Field(default_factory=list)

    _clean_citations = field_validator("citations", mode="before")(_sanitize_citations)


class Risk(BaseModel):
    title: str
    description: str
    severity: Priority
    citations: list[Citation] = Field(default_factory=list)

    _clean_citations = field_validator("citations", mode="before")(_sanitize_citations)


class Recommendation(BaseModel):
    action: str
    priority: Priority
    rationale: str
    confidence: Confidence
    dependencies: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    _clean_citations = field_validator("citations", mode="before")(_sanitize_citations)


class ValidationStep(BaseModel):
    step: str
    rationale: str


class KnowledgeSource(BaseModel):
    """A knowledge base chunk that was retrieved and provided to the agent.

    Populated by the pipeline (not the LLM), so grounding is always visible even
    when the model does not tag individual claims with citations.
    """

    chunk_id: str
    title: str | None = None
    topic: str | None = None
    source: str | None = None
    snippet: str | None = None


class ReportMetadata(BaseModel):
    agent_model: str
    prompt_version: str
    generated_at: str


class AnalysisReport(BaseModel):
    session_id: str
    overview: str
    channel_ranking: list[str] = Field(
        default_factory=list,
        description=(
            "The agent's own ranking of every channel from most to least "
            "effective (by overall/marginal ROI, accounting for uncertainty and "
            "saturation). Must list each channel name exactly once. This is the "
            "agent's judgment, which may differ from the raw ROI point estimates."
        ),
    )
    per_channel: list[ChannelAnalysis] = Field(default_factory=list)
    structural_risks: list[Risk] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    validation_suggestions: list[ValidationStep] = Field(default_factory=list)
    knowledge_sources: list[KnowledgeSource] = Field(default_factory=list)
    metadata: ReportMetadata
