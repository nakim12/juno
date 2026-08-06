"""CLI for judge validation (design doc 9.2).

Reliability (test-retest self-consistency) — runnable now, no human needed::

    python -m app.evaluation.validate_judge --reliability --n 3 --k 3

Generate a human-labelling template (pre-filled with the judge's scores)::

    python -m app.evaluation.validate_judge --template --n 20

After filling in the ``human_score`` fields, compute judge-vs-human agreement::

    python -m app.evaluation.validate_judge --validity

Add ``--no-llm-agent`` to score the free heuristic agent's reports instead of
the live LLM agent (useful for cheap dry runs of the validation machinery).
"""

from __future__ import annotations

import argparse
import asyncio

from app.evaluation import benchmark_generator as bg
from app.evaluation import judge_validation as jv


def _print_reliability(res: jv.ReliabilityResult) -> None:
    print("\n" + "=" * 64)
    print(f"  Judge reliability (test-retest) — {res.n_cases} cases × {res.k_repetitions} reps")
    print("=" * 64)
    print(f"  {'Dimension':<24}{'mean σ':>10}{'identical':>12}{'kappa':>10}")
    print("  " + "-" * 56)
    for dim, stats in res.per_dimension.items():
        print(
            f"  {dim:<24}{stats['mean_std']:>10.3f}"
            f"{stats['all_identical_rate']:>12.2f}{stats['test_retest_kappa']:>10.3f}"
        )
    print("  " + "-" * 56)
    print(f"  Overall test-retest kappa: {res.overall_kappa:.3f}")
    print("  (kappa > 0.6 substantial, > 0.8 near-perfect; lower mean σ is better)")
    print("=" * 64 + "\n")


def _print_validity(result: dict) -> None:
    print("\n" + "=" * 64)
    print("  Judge validity (agreement with human labels)")
    print("=" * 64)
    print(f"  {'Dimension':<24}{'exact':>8}{'±1':>8}{'kappa':>9}{'MAE':>8}")
    print("  " + "-" * 56)
    for dim, s in result.items():
        print(
            f"  {dim:<24}{s['exact_match']:>8.2f}{s['within_one']:>8.2f}"
            f"{s['kappa']:>9.3f}{s['mean_abs_error']:>8.2f}"
        )
    print("=" * 64 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the LLM-as-judge.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--reliability", action="store_true", help="test-retest self-consistency")
    mode.add_argument("--template", action="store_true", help="write a human-labelling template")
    mode.add_argument("--validity", action="store_true", help="compute agreement vs human labels")
    parser.add_argument("--n", type=int, default=3, help="number of cases")
    parser.add_argument("--k", type=int, default=3, help="judge repetitions (reliability)")
    parser.add_argument("--version", default="v1", help="benchmark version tag")
    parser.add_argument("--no-llm-agent", action="store_true", help="score heuristic reports")
    args = parser.parse_args()

    if args.validity:
        try:
            _print_validity(jv.compute_validity(args.version))
        except (FileNotFoundError, ValueError) as exc:
            print(f"\nCannot compute validity yet: {exc}\n")
        return

    try:
        cases = bg.load_benchmark(args.version)[: args.n]
    except FileNotFoundError:
        cases = bg.generate_cases(args.n)
        bg.save_benchmark(cases, args.version)
    print(f"Using {len(cases)} cases from benchmark '{args.version}'.")

    use_llm_agent = not args.no_llm_agent
    if args.reliability:
        res = asyncio.run(
            jv.measure_reliability(
                cases, version=args.version, k=args.k, use_llm_agent=use_llm_agent
            )
        )
        _print_reliability(res)
    elif args.template:
        path = asyncio.run(
            jv.write_labeling_template(cases, version=args.version, use_llm_agent=use_llm_agent)
        )
        print(f"\nWrote labelling template -> {path}")
        print("Fill in each `human_score` (0-5), then run: "
              "python -m app.evaluation.validate_judge --validity\n")


if __name__ == "__main__":
    main()
