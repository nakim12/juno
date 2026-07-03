"""Structured, deterministic summary produced by the parser (design doc 5.1)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChannelSummary(BaseModel):
    name: str
    total_spend: float
    roi_point: float
    roi_ci: tuple[float, float]
    ci_width: float = Field(..., description="Absolute width of the ROI credible interval.")
    adstock_decay: float
    half_saturation: float
    contribution_pct: float


class DetectedIssue(BaseModel):
    code: str = Field(..., description="Machine-readable issue code, e.g. 'wide_ci'.")
    channel: str | None = None
    detail: str


class MMMSummary(BaseModel):
    """Deterministic representation of an MMM output. No LLM involved."""

    model_type: str
    data_span_weeks: int | None
    n_channels: int
    total_spend: float
    channels: list[ChannelSummary]
    r_squared: float | None = None
    mape: float | None = None
    detected_issues: list[DetectedIssue] = Field(default_factory=list)

    def ranked_channels(self) -> list[str]:
        """Channel names sorted by ROI point estimate, descending."""
        return [c.name for c in sorted(self.channels, key=lambda c: c.roi_point, reverse=True)]
