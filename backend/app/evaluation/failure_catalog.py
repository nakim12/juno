"""Failure mode catalog logging (design doc 5.4, 9.4).

Persists low-scoring agent responses with the judge's reasoning so a taxonomy of
failure modes can be built over time (target: >= 10 categorized entries).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS failure_modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT,
    case_id TEXT NOT NULL,
    category TEXT,
    agent_response TEXT NOT NULL,
    judge_reasoning TEXT NOT NULL,
    score REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class FailureEntry:
    case_id: str
    agent_response: str
    judge_reasoning: str
    score: float
    category: str | None = None
    run_id: str | None = None


def _connect() -> sqlite3.Connection:
    Path(settings.eval_db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.eval_db_path)
    conn.execute(SCHEMA)
    return conn


def log_failure(entry: FailureEntry) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO failure_modes (run_id, case_id, category, agent_response,"
            " judge_reasoning, score) VALUES (?, ?, ?, ?, ?, ?)",
            (
                entry.run_id,
                entry.case_id,
                entry.category,
                entry.agent_response,
                entry.judge_reasoning,
                entry.score,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def all_failures() -> list[dict]:
    conn = _connect()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM failure_modes ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
