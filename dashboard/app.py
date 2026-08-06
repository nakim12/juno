"""Juno evaluation dashboard (design doc 5.4).

A Streamlit app that surfaces evaluation metrics, trends across runs, the
per-scenario breakdown, and the failure-mode catalog. Point it at the eval
SQLite DB produced by the benchmark runner.

Run:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
import sqlite3

import streamlit as st

DB_PATH = os.environ.get("JUNO_EVAL_DB", "backend/data/eval.db")

st.set_page_config(page_title="Juno · Eval Dashboard", layout="wide")
st.title("Juno — Evaluation Dashboard")
st.caption(
    "Metrics and failure-mode catalog for the MMM Copilot agent. See design doc §5.4 / §9."
)

# (label, db column, target text, pass predicate, formatter)
DIMENSIONS = [
    ("Accuracy (Spearman)", "accuracy", "> 0.85", lambda v: v > 0.85, "{:.3f}"),
    ("Calibration (ECE)", "calibration_ece", "< 0.10", lambda v: v < 0.10, "{:.3f}"),
    ("Groundedness", "groundedness", "> 0.90", lambda v: v > 0.90, "{:.3f}"),
    ("Actionability", "actionability", "> 4.0 / 5", lambda v: v > 4.0, "{:.2f}"),
    ("Failure recall", "failure_mode_recall", "> 0.75", lambda v: v > 0.75, "{:.3f}"),
    ("Hallucination", "hallucination_rate", "< 0.05", lambda v: v < 0.05, "{:.3f}"),
]


def _load(query: str) -> list[dict]:
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(query).fetchall()]
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


if not os.path.exists(DB_PATH):
    st.info(
        f"No eval database found at `{DB_PATH}`. Run the benchmark suite:\n\n"
        "`cd backend && python -m app.evaluation.run_eval --n 20 --no-llm --no-judge`"
    )
    st.stop()

runs = _load("SELECT * FROM eval_runs ORDER BY created_at ASC")

if not runs:
    st.warning(
        "No evaluation runs recorded yet. Run:\n\n"
        "`cd backend && python -m app.evaluation.run_eval --n 20 --no-llm --no-judge`"
    )
else:
    latest = runs[-1]
    st.subheader("Latest run")
    st.caption(
        f"{latest['n_cases']} cases · agent `{latest['agent_model']}` · "
        f"judge `{latest['judge_model']}` · prompt `{latest['prompt_version']}` · "
        f"{latest['created_at']}"
    )

    cols = st.columns(len(DIMENSIONS))
    for col, (label, key, target, passes, fmt) in zip(cols, DIMENSIONS):
        value = latest.get(key)
        judged = key in ("groundedness", "actionability", "hallucination_rate")
        if value is None or (judged and not latest.get("used_judge")):
            col.metric(label, "—", help=f"Target: {target}")
        else:
            ok = passes(value)
            col.metric(
                label,
                fmt.format(value),
                delta=("on target" if ok else "off target"),
                delta_color=("normal" if ok else "inverse"),
                help=f"Target: {target}",
            )
    st.metric("Weighted total", f"{latest.get('weighted_total', 0):.3f}")

    if len(runs) > 1:
        st.divider()
        st.subheader("Trend across runs")
        chart_data = {
            "accuracy": [r["accuracy"] for r in runs],
            "groundedness": [r["groundedness"] for r in runs],
            "failure_mode_recall": [r["failure_mode_recall"] for r in runs],
            "weighted_total": [r["weighted_total"] for r in runs],
        }
        st.line_chart(chart_data)

    breakdown = latest.get("scenario_breakdown")
    if breakdown:
        try:
            parsed = json.loads(breakdown)
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        if parsed:
            st.divider()
            st.subheader("Per-scenario breakdown (latest run)")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Accuracy by channel count")
                st.bar_chart(parsed.get("accuracy_by_channel_count", {}))
            with c2:
                st.caption("Failure-mode recall by mode")
                st.bar_chart(parsed.get("recall_by_failure_mode", {}))

st.divider()
st.subheader("Failure Mode Catalog")
failures = _load(
    "SELECT created_at, run_id, case_id, category, score, judge_reasoning "
    "FROM failure_modes ORDER BY created_at DESC"
)
if failures:
    categories = sorted({f["category"] for f in failures if f["category"]})
    chosen = st.multiselect("Filter by category", categories, default=categories)
    filtered = [f for f in failures if f["category"] in chosen] if chosen else failures
    st.caption(f"{len(filtered)} entries")
    st.dataframe(filtered, use_container_width=True)
else:
    st.success("No failures logged yet.")
