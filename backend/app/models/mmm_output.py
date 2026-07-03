"""Input schema: raw MMM output uploaded or loaded from a sample.

Mirrors the data model in the design doc (section 5.7). This is the contract
between the BlueAlpha simulator (or any MMM tool) and Juno.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SaturationParams(BaseModel):
    """Hill-style saturation parameters."""

    half_saturation: float = Field(
        ..., description="Spend level at which the channel reaches half of its max effect."
    )
    shape: float = Field(1.0, description="Hill exponent controlling curve steepness.")


class ChannelOutput(BaseModel):
    name: str
    spend_weekly: list[float] = Field(default_factory=list, description="Weekly spend series.")
    roi_point: float = Field(..., description="Point estimate of return on investment.")
    roi_ci: tuple[float, float] = Field(..., description="(lower, upper) 95% credible interval.")
    adstock_decay: float = Field(..., ge=0.0, le=1.0, description="Geometric adstock decay rate.")
    saturation_params: SaturationParams
    contribution_pct: float = Field(..., description="Share of total attributed outcome (0-1).")


class Diagnostics(BaseModel):
    r_squared: float | None = None
    mape: float | None = None
    holdout_mape: float | None = None
    nrmse: float | None = None


class MMMMetadata(BaseModel):
    model_type: str = Field("unknown", description="e.g. bayesian, robyn, meridian, custom.")
    data_span_weeks: int | None = None
    generated_at: str | None = None
    source: str | None = Field(None, description="Where this output came from, e.g. 'bluealpha'.")


class ExtendedData(BaseModel):
    """Optional priors / MCMC diagnostics that some models emit."""

    priors: dict[str, float] | None = None
    rhat_max: float | None = None
    divergences: int | None = None


class MMMOutput(BaseModel):
    metadata: MMMMetadata
    channels: list[ChannelOutput]
    model_diagnostics: Diagnostics = Field(default_factory=Diagnostics)
    optional: ExtendedData | None = None
