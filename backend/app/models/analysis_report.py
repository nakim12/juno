"""Output schema for the initial analysis pipeline (design doc 5.1 / 5.7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]
Priority = Literal["high", "medium", "low"]


class Citation(BaseModel):
    """A grounding pointer to either the MMM output or a knowledge base chunk."""

    source_type: Literal["mmm_output", "knowledge_base"]
    reference: str = Field(..., description="Channel/field name, or KB chunk id.")
    snippet: str | None = None


class ChannelAnalysis(BaseModel):
    channel_name: str
    interpretation: str
    confidence: Confidence
    confidence_reasoning: str
    citations: list[Citation] = Field(default_factory=list)


class Risk(BaseModel):
    title: str
    description: str
    severity: Priority
    citations: list[Citation] = Field(default_factory=list)


class Recommendation(BaseModel):
    action: str
    priority: Priority
    rationale: str
    confidence: Confidence
    dependencies: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ValidationStep(BaseModel):
    step: str
    rationale: str


class ReportMetadata(BaseModel):
    agent_model: str
    prompt_version: str
    generated_at: str


class AnalysisReport(BaseModel):
    session_id: str
    overview: str
    per_channel: list[ChannelAnalysis] = Field(default_factory=list)
    structural_risks: list[Risk] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    validation_suggestions: list[ValidationStep] = Field(default_factory=list)
    metadata: ReportMetadata
