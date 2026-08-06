"""CLI entrypoint for the evaluation harness.

Examples
--------
Fast, free smoke test (heuristic agent, no judge, deterministic metrics only)::

    python -m app.evaluation.run_eval --n 20 --no-llm --no-judge

Full run with the live agent (Sonnet) and judge (Opus)::

    python -m app.evaluation.run_eval --n 50

Results are persisted to the eval SQLite DB and surfaced in the dashboard.
"""

from __future__ import annotations

import argparse
import asyncio

from app.evaluation import benchmark_generator as bg
from app.evaluation import reports_cache, runner
from app.evaluation.results_store import RunRecord

_TARGETS = {
    "accuracy": ("Accuracy (Spearman)", "> 0.85", lambda v: v > 0.85),
    "calibration_ece": ("Calibration (ECE)", "< 0.10", lambda v: v < 0.10),
    "groundedness": ("Groundedness", "> 0.90", lambda v: v > 0.90),
    "actionability": ("Actionability (/5)", "> 4.0", lambda v: v > 4.0),
    "failure_mode_recall": ("Failure recall", "> 0.75", lambda v: v > 0.75),
    "hallucination_rate": ("Hallucination", "< 0.05", lambda v: v < 0.05),
}


def _print_report(record: RunRecord, used_judge: bool) -> None:
    print("\n" + "=" * 64)
    print(f"  Juno evaluation — {record.n_cases} cases")
    print(f"  agent={record.agent_model}  judge={record.judge_model}")
    print(f"  prompt={record.prompt_version}  run_id={record.run_id}")
    print("=" * 64)
    print(f"  {'Dimension':<24}{'Score':>10}{'Target':>12}{'Pass':>8}")
    print("  " + "-" * 52)
    for key, (label, target, ok) in _TARGETS.items():
        value = getattr(record, key)
        judged_only = key in ("groundedness", "actionability", "hallucination_rate")
        if judged_only and not used_judge:
            print(f"  {label:<24}{'—':>10}{target:>12}{'(no judge)':>10}")
            continue
        mark = "✓" if ok(value) else "✗"
        print(f"  {label:<24}{value:>10.3f}{target:>12}{mark:>8}")
    print("  " + "-" * 52)
    print(f"  {'Weighted total':<24}{record.weighted_total:>10.3f}")
    print("=" * 64)
    if record.scenario_breakdown:
        print("  Accuracy by channel count:",
              record.scenario_breakdown.get("accuracy_by_channel_count"))
        print("  Recall by failure mode:   ",
              record.scenario_breakdown.get("recall_by_failure_mode"))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Juno evaluation benchmark.")
    parser.add_argument("--n", type=int, default=20, help="number of benchmark cases")
    parser.add_argument("--seed", type=int, default=42, help="simulator seed")
    parser.add_argument("--version", default="v1", help="benchmark set version tag")
    parser.add_argument("--no-llm", action="store_true", help="use heuristic agent (free)")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM judge")
    parser.add_argument("--regenerate", action="store_true", help="regenerate the benchmark set")
    parser.add_argument("--no-persist", action="store_true", help="do not write to the DB")
    parser.add_argument(
        "--concurrency", type=int, default=4,
        help="number of cases to run in parallel (rate limits are retried)",
    )
    parser.add_argument(
        "--use-cached-reports", action="store_true",
        help="re-score cached agent reports instead of re-running the agent "
             "(cheap judge-only run; only the Opus judge costs money)",
    )
    args = parser.parse_args()

    try:
        if args.regenerate:
            raise FileNotFoundError
        cases = bg.load_benchmark(args.version)
        if len(cases) != args.n:
            cases = cases[: args.n] if len(cases) > args.n else cases
        print(f"Loaded benchmark '{args.version}' ({len(cases)} cases).")
    except FileNotFoundError:
        cases = bg.generate_cases(args.n, seed=args.seed)
        path = bg.save_benchmark(cases, args.version)
        print(f"Generated {len(cases)} cases -> {path}")

    cached_reports = None
    if args.use_cached_reports:
        cached_reports = reports_cache.load_reports(args.version)
        hits = sum(1 for c in cases if c.case_id in cached_reports)
        print(f"Re-scoring {hits}/{len(cases)} cases from cached reports (no agent calls).")

    record = asyncio.run(
        runner.run_suite(
            cases,
            use_llm=not args.no_llm,
            use_judge=not args.no_judge,
            version=args.version,
            persist=not args.no_persist,
            concurrency=args.concurrency,
            cached_reports=cached_reports,
        )
    )
    _print_report(record, used_judge=not args.no_judge)


if __name__ == "__main__":
    main()
