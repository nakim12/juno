"""Deterministic MMM structure extraction (design doc 5.1, Stage 1).

This module is intentionally NOT an LLM call. It turns a raw ``MMMOutput`` into
a compact ``MMMSummary`` and flags obvious structural issues that downstream
agents (and the eval harness) should be aware of.
"""

from __future__ import annotations

from app.models.mmm_output import MMMOutput
from app.models.mmm_summary import ChannelSummary, DetectedIssue, MMMSummary

# Heuristic thresholds. Tune these as the corpus / benchmark evolves.
WIDE_CI_RATIO = 1.0  # CI width >= ROI point estimate => "wide"
HIGH_ADSTOCK = 0.9  # very persistent carryover
LOW_CONTRIBUTION = 0.02  # channel contributing < 2%


def _detect_issues(summary_channels: list[ChannelSummary]) -> list[DetectedIssue]:
    issues: list[DetectedIssue] = []
    for ch in summary_channels:
        if ch.roi_point > 0 and ch.ci_width >= WIDE_CI_RATIO * ch.roi_point:
            issues.append(
                DetectedIssue(
                    code="wide_ci",
                    channel=ch.name,
                    detail=(
                        f"ROI CI for {ch.name} is wide "
                        f"({ch.roi_ci[0]:.2f}-{ch.roi_ci[1]:.2f}) relative to the point "
                        f"estimate ({ch.roi_point:.2f}); treat ROI with low confidence."
                    ),
                )
            )
        if ch.adstock_decay >= HIGH_ADSTOCK:
            issues.append(
                DetectedIssue(
                    code="high_adstock",
                    channel=ch.name,
                    detail=(
                        f"{ch.name} has very high adstock decay ({ch.adstock_decay:.2f}); "
                        "effects persist for many weeks and may be hard to identify."
                    ),
                )
            )
        if ch.contribution_pct < LOW_CONTRIBUTION:
            issues.append(
                DetectedIssue(
                    code="low_contribution",
                    channel=ch.name,
                    detail=f"{ch.name} contributes < 2% of attributed outcome.",
                )
            )
    return issues


def parse(mmm: MMMOutput) -> MMMSummary:
    """Convert a raw MMM output into a deterministic summary."""
    channels: list[ChannelSummary] = []
    for ch in mmm.channels:
        lower, upper = ch.roi_ci
        channels.append(
            ChannelSummary(
                name=ch.name,
                total_spend=float(sum(ch.spend_weekly)),
                roi_point=ch.roi_point,
                roi_ci=ch.roi_ci,
                ci_width=abs(upper - lower),
                adstock_decay=ch.adstock_decay,
                half_saturation=ch.saturation_params.half_saturation,
                contribution_pct=ch.contribution_pct,
            )
        )

    summary = MMMSummary(
        model_type=mmm.metadata.model_type,
        data_span_weeks=mmm.metadata.data_span_weeks,
        n_channels=len(channels),
        total_spend=float(sum(c.total_spend for c in channels)),
        channels=channels,
        r_squared=mmm.model_diagnostics.r_squared,
        mape=mmm.model_diagnostics.mape,
    )
    summary.detected_issues = _detect_issues(channels)
    return summary
