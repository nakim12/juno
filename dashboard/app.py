"""Juno evaluation dashboard (design doc 5.4).

A Streamlit app that surfaces evaluation metrics and the failure mode catalog.
Point it at the eval SQLite DB produced by the benchmark runner.

Run:  streamlit run dashboard/app.py
"""

from __future__ import annotations

import os
import sqlite3

import streamlit as st

DB_PATH = os.environ.get("JUNO_EVAL_DB", "backend/data/eval.db")

st.set_page_config(page_title="Juno · Eval Dashboard", layout="wide")
st.title("Juno — Evaluation Dashboard")
st.caption(
    "Metrics and failure-mode catalog for the MMM Copilot agent. "
    "See design doc §5.4 / §9."
)

# Placeholder metric cards until the benchmark runner has produced results.
cols = st.columns(6)
targets = [
    ("Accuracy (Spearman)", "—", "> 0.85"),
    ("Calibration (ECE)", "—", "< 0.10"),
    ("Groundedness", "—", "> 0.90"),
    ("Actionability", "—", "> 4.0 / 5"),
    ("Failure recall", "—", "> 0.75"),
    ("Hallucination", "—", "< 0.05"),
]
for col, (label, value, target) in zip(cols, targets):
    col.metric(label, value, help=f"Target: {target}")

st.divider()
st.subheader("Failure Mode Catalog")

if not os.path.exists(DB_PATH):
    st.info(
        f"No eval database found at `{DB_PATH}`. Run the benchmark suite "
        "(`backend/app/evaluation/runner.py`) to populate metrics and failures."
    )
else:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT case_id, category, score, judge_reasoning, created_at "
            "FROM failure_modes ORDER BY created_at DESC"
        ).fetchall()
        if rows:
            st.dataframe([dict(r) for r in rows], use_container_width=True)
        else:
            st.success("No failures logged yet.")
    except sqlite3.OperationalError:
        st.warning("Eval DB exists but has no failure_modes table yet.")
    finally:
        conn.close()
