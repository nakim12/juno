"""Benchmark set generation (design doc 5.4, 7.3).

Wraps the BlueAlpha simulator to produce N diverse MMM output scenarios with
known ground truth. The simulator interface is deferred (open question 13.3):
this module defines the contract and a placeholder so the harness can be built
against a stable shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.mmm_output import MMMOutput


@dataclass
class GroundTruth:
    true_roi: dict[str, float]
    optimal_allocation: dict[str, float]
    known_failure_modes: list[str] = field(default_factory=list)


@dataclass
class BenchmarkCase:
    case_id: str
    mmm_output: MMMOutput
    ground_truth: GroundTruth


def generate_cases(n: int = 100) -> list[BenchmarkCase]:
    """Generate ``n`` benchmark cases via the BlueAlpha simulator.

    TODO: wire the actual BlueAlpha simulator (see design doc open question 3).
    Sweep channel count (3-10), spend range, seasonality, adstock decay,
    saturation shape, noise, and data span (26-104 weeks).
    """
    raise NotImplementedError(
        "Connect the BlueAlpha simulator here. See design doc section 5.4 / 13."
    )
