"""Benchmark set generation (design doc 5.4, 7.3).

The design doc assumes access to the external "BlueAlpha simulator" for ground
truth (open question 13.3). That dependency is not available here, so this module
instead implements a **self-contained synthetic MMM simulator**. Because we
construct each scenario, the ground truth (true per-channel ROI, saturation and
adstock parameters, optimal allocation, and injected failure modes) is known by
construction — which is exactly what an evaluation harness needs.

The simulator sweeps the scenario dimensions the design doc calls for (channel
count, spend range, seasonality, adstock decay, saturation shape, noise, and data
span) and is fully seeded for reproducibility. Generated sets can be saved to and
loaded from versioned JSON under ``evaluation/benchmarks/``.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.models.mmm_output import (
    ChannelOutput,
    Diagnostics,
    MMMMetadata,
    MMMOutput,
    SaturationParams,
)

# Versioned benchmark sets live here (checked in so eval runs are reproducible).
# __file__ = backend/app/evaluation/benchmark_generator.py; parents[3] = project root.
BENCHMARKS_DIR = Path(__file__).resolve().parents[3] / "evaluation" / "benchmarks"

_CHANNEL_NAMES = [
    "Search",
    "Social",
    "Display",
    "Video",
    "TV",
    "Radio",
    "Email",
    "Affiliate",
    "Podcast",
    "OOH",
]

# Known failure-mode tags. Each maps to a detector in ``metrics.detected_failure_modes``
# so we can measure the agent's recall on flagging them.
FAILURE_WIDE_CI = "wide_ci"
FAILURE_HIGH_ADSTOCK = "high_adstock"
FAILURE_LOW_CONTRIBUTION = "low_contribution"
FAILURE_MULTICOLLINEARITY = "multicollinearity"
FAILURE_SATURATION = "saturation_extrapolation"


@dataclass
class GroundTruth:
    true_roi: dict[str, float]
    true_half_saturation: dict[str, float]
    true_adstock: dict[str, float]
    optimal_allocation: dict[str, float]
    known_failure_modes: list[str] = field(default_factory=list)

    def true_ranking(self) -> list[str]:
        ranked = sorted(self.true_roi.items(), key=lambda kv: kv[1], reverse=True)
        return [name for name, _ in ranked]


@dataclass
class BenchmarkCase:
    case_id: str
    mmm_output: MMMOutput
    ground_truth: GroundTruth
    scenario: dict  # sweep parameters, for per-scenario-type breakdowns

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "mmm_output": self.mmm_output.model_dump(),
            "ground_truth": asdict(self.ground_truth),
            "scenario": self.scenario,
        }

    @classmethod
    def from_dict(cls, data: dict) -> BenchmarkCase:
        return cls(
            case_id=data["case_id"],
            mmm_output=MMMOutput.model_validate(data["mmm_output"]),
            ground_truth=GroundTruth(**data["ground_truth"]),
            scenario=data.get("scenario", {}),
        )


def _weekly_spend(
    rng: random.Random, weeks: int, base: float, seasonality: float
) -> list[float]:
    """Weekly spend with a seasonal component and mild noise."""
    series = []
    for w in range(weeks):
        season = 1.0 + seasonality * math.sin(2 * math.pi * w / 52.0)
        noise = rng.uniform(0.9, 1.1)
        series.append(round(base * season * noise, 2))
    return series


def _correlated_spend(base_series: list[float], rng: random.Random) -> list[float]:
    """A spend series highly correlated with ``base_series`` (multicollinearity)."""
    scale = rng.uniform(0.8, 1.2)
    return [round(v * scale * rng.uniform(0.98, 1.02), 2) for v in base_series]


def _generate_case(rng: random.Random, case_id: str) -> BenchmarkCase:
    n_channels = rng.randint(3, 10)
    weeks = rng.choice([26, 39, 52, 78, 104])
    seasonality = rng.uniform(0.0, 0.4)
    noise_level = rng.uniform(0.05, 0.35)  # drives CI width relative to point est

    names = rng.sample(_CHANNEL_NAMES, n_channels)

    # Decide which failure modes this scenario carries.
    failure_modes: list[str] = []
    inject_wide_ci = rng.random() < 0.4
    inject_high_adstock = rng.random() < 0.3
    inject_low_contribution = rng.random() < 0.3
    inject_multicollinearity = n_channels >= 4 and rng.random() < 0.35
    inject_saturation = rng.random() < 0.4

    true_roi: dict[str, float] = {}
    true_half_sat: dict[str, float] = {}
    true_adstock: dict[str, float] = {}
    channels: list[ChannelOutput] = []

    # Raw contribution weights (normalized later).
    raw_weights: dict[str, float] = {}
    base_series_for_collinearity: list[float] | None = None

    for i, name in enumerate(names):
        roi = round(rng.uniform(0.5, 5.0), 2)
        base_spend = rng.uniform(2_000, 60_000)
        half_sat = round(base_spend * weeks * rng.uniform(0.5, 1.5), 2)
        adstock = round(rng.uniform(0.1, 0.85), 2)

        # Injected: very persistent carryover on the first channel.
        if inject_high_adstock and i == 0:
            adstock = round(rng.uniform(0.9, 0.97), 2)
            failure_modes.append(FAILURE_HIGH_ADSTOCK)

        # Spend series (with an optional collinear twin).
        if inject_multicollinearity and i == 1 and base_series_for_collinearity:
            spend = _correlated_spend(base_series_for_collinearity, rng)
            if FAILURE_MULTICOLLINEARITY not in failure_modes:
                failure_modes.append(FAILURE_MULTICOLLINEARITY)
        else:
            spend = _weekly_spend(rng, weeks, base_spend, seasonality)
            if i == 0:
                base_series_for_collinearity = spend

        # The reported point estimate is the true ROI perturbed by estimation noise.
        est_roi = max(0.05, round(roi * rng.uniform(1 - noise_level, 1 + noise_level), 2))
        half_width = est_roi * noise_level

        # Injected: pathologically wide CI on one channel.
        if inject_wide_ci and i == min(2, n_channels - 1):
            half_width = est_roi * rng.uniform(0.6, 1.1)
            if FAILURE_WIDE_CI not in failure_modes:
                failure_modes.append(FAILURE_WIDE_CI)

        ci = (round(max(0.0, est_roi - half_width), 2), round(est_roi + half_width, 2))

        # Injected: current spend far above the saturation point (extrapolation risk).
        if inject_saturation and i == 0:
            half_sat = round(sum(spend) * rng.uniform(0.3, 0.6), 2)
            if FAILURE_SATURATION not in failure_modes:
                failure_modes.append(FAILURE_SATURATION)

        raw_weights[name] = est_roi * sum(spend)
        true_roi[name] = roi
        true_half_sat[name] = half_sat
        true_adstock[name] = adstock

        channels.append(
            ChannelOutput(
                name=name,
                spend_weekly=spend,
                roi_point=est_roi,
                roi_ci=ci,
                adstock_decay=adstock,
                saturation_params=SaturationParams(
                    half_saturation=half_sat, shape=round(rng.uniform(0.8, 2.0), 2)
                ),
                contribution_pct=0.0,  # filled after normalization
            )
        )

    # Normalize contributions to sum to 1.
    total_weight = sum(raw_weights.values()) or 1.0
    for ch in channels:
        ch.contribution_pct = round(raw_weights[ch.name] / total_weight, 4)

    # Injected: force one channel below the 2% contribution threshold.
    if inject_low_contribution and len(channels) >= 3:
        victim = channels[-1]
        victim.contribution_pct = round(rng.uniform(0.002, 0.018), 4)
        if FAILURE_LOW_CONTRIBUTION not in failure_modes:
            failure_modes.append(FAILURE_LOW_CONTRIBUTION)

    # Optimal allocation: proportional to true ROI (a defensible first-order proxy;
    # a marginal-ROI optimizer over the saturation curves is a future refinement).
    roi_sum = sum(true_roi.values()) or 1.0
    optimal_allocation = {name: round(r / roi_sum, 4) for name, r in true_roi.items()}

    mmm = MMMOutput(
        metadata=MMMMetadata(
            model_type="bayesian",
            data_span_weeks=weeks,
            source="synthetic-simulator",
        ),
        channels=channels,
        model_diagnostics=Diagnostics(
            r_squared=round(rng.uniform(0.7, 0.95), 3),
            mape=round(rng.uniform(0.05, 0.25), 3),
            holdout_mape=round(rng.uniform(0.08, 0.30), 3),
        ),
    )

    scenario = {
        "n_channels": n_channels,
        "weeks": weeks,
        "seasonality": round(seasonality, 3),
        "noise_level": round(noise_level, 3),
        "failure_modes": failure_modes,
    }
    return BenchmarkCase(
        case_id=case_id,
        mmm_output=mmm,
        ground_truth=GroundTruth(
            true_roi=true_roi,
            true_half_saturation=true_half_sat,
            true_adstock=true_adstock,
            optimal_allocation=optimal_allocation,
            known_failure_modes=sorted(set(failure_modes)),
        ),
        scenario=scenario,
    )


def generate_cases(n: int = 100, seed: int = 42) -> list[BenchmarkCase]:
    """Generate ``n`` synthetic benchmark cases with known ground truth.

    Seeded for reproducibility. Sweeps channel count (3-10), spend range,
    seasonality, adstock decay, saturation shape, noise, and data span
    (26-104 weeks), injecting tagged failure modes into a subset of cases.
    """
    rng = random.Random(seed)
    return [_generate_case(rng, f"case_{i:04d}") for i in range(n)]


def save_benchmark(cases: list[BenchmarkCase], version: str = "v1") -> Path:
    BENCHMARKS_DIR.mkdir(parents=True, exist_ok=True)
    path = BENCHMARKS_DIR / f"benchmark_{version}.json"
    path.write_text(
        json.dumps([c.to_dict() for c in cases], indent=2), encoding="utf-8"
    )
    return path


def load_benchmark(version: str = "v1") -> list[BenchmarkCase]:
    path = BENCHMARKS_DIR / f"benchmark_{version}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return [BenchmarkCase.from_dict(d) for d in data]
