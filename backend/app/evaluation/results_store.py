"""Persistence for evaluation runs (design doc 5.4 dashboard, 9.3 regression).

Stores one row per benchmark run with the aggregate dimension scores plus the
agent/judge configuration, so the dashboard can trend metrics across prompt
versions and flag regressions. Uses the same SQLite file as the failure catalog.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings

RUNS_SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_runs (
    run_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    n_cases INTEGER NOT NULL,
    agent_model TEXT,
    judge_model TEXT,
    prompt_version TEXT,
    used_llm INTEGER NOT NULL,
    used_judge INTEGER NOT NULL,
    accuracy REAL,
    calibration_ece REAL,
    groundedness REAL,
    actionability REAL,
    failure_mode_recall REAL,
    hallucination_rate REAL,
    weighted_total REAL,
    scenario_breakdown TEXT
);
"""

# One row per (case, channel) capturing the agent's stated confidence and whether
# it ranked that channel correctly — the raw material for a reliability diagram
# and for tuning the confidence->probability mapping.
CALIBRATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS calibration_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    case_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    confidence TEXT NOT NULL,
    prob REAL NOT NULL,
    correct INTEGER NOT NULL,
    agent_rank INTEGER,
    true_rank INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class RunRecord:
    n_cases: int
    accuracy: float
    calibration_ece: float
    groundedness: float
    actionability: float
    failure_mode_recall: float
    hallucination_rate: float
    weighted_total: float
    agent_model: str = ""
    judge_model: str = ""
    prompt_version: str = ""
    used_llm: bool = False
    used_judge: bool = False
    scenario_breakdown: dict = field(default_factory=dict)
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass
class CalibrationPoint:
    run_id: str
    case_id: str
    channel: str
    confidence: str
    prob: float
    correct: bool
    agent_rank: int | None = None
    true_rank: int | None = None


def _connect() -> sqlite3.Connection:
    Path(settings.eval_db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.eval_db_path)
    conn.execute(RUNS_SCHEMA)
    conn.execute(CALIBRATION_SCHEMA)
    return conn


def save_run(record: RunRecord) -> str:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO eval_runs (run_id, created_at, n_cases, agent_model, judge_model,"
            " prompt_version, used_llm, used_judge, accuracy, calibration_ece, groundedness,"
            " actionability, failure_mode_recall, hallucination_rate, weighted_total,"
            " scenario_breakdown) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.run_id,
                datetime.now(UTC).isoformat(),
                record.n_cases,
                record.agent_model,
                record.judge_model,
                record.prompt_version,
                int(record.used_llm),
                int(record.used_judge),
                record.accuracy,
                record.calibration_ece,
                record.groundedness,
                record.actionability,
                record.failure_mode_recall,
                record.hallucination_rate,
                record.weighted_total,
                json.dumps(record.scenario_breakdown),
            ),
        )
        conn.commit()
        return record.run_id
    finally:
        conn.close()


def all_runs() -> list[dict]:
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM eval_runs ORDER BY created_at ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def save_calibration_points(points: list[CalibrationPoint]) -> int:
    """Bulk-insert per-channel calibration points. Returns the number written."""
    if not points:
        return 0
    conn = _connect()
    try:
        conn.executemany(
            "INSERT INTO calibration_points (run_id, case_id, channel, confidence,"
            " prob, correct, agent_rank, true_rank) VALUES (?,?,?,?,?,?,?,?)",
            [
                (
                    p.run_id,
                    p.case_id,
                    p.channel,
                    p.confidence,
                    p.prob,
                    int(p.correct),
                    p.agent_rank,
                    p.true_rank,
                )
                for p in points
            ],
        )
        conn.commit()
        return len(points)
    finally:
        conn.close()


def calibration_points_for_run(run_id: str) -> list[dict]:
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM calibration_points WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def latest_calibrated_run_id() -> str | None:
    """The most recent run_id that has calibration points recorded."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT run_id FROM calibration_points ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()
