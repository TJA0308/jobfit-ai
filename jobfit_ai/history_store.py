from __future__ import annotations

import sqlite3
from pathlib import Path

from jobfit_ai.models import HistoryEntry, ResumeAnalysis

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "jobfit_ai.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                candidate_name TEXT NOT NULL,
                source_filename TEXT NOT NULL,
                source_type TEXT NOT NULL,
                target_role TEXT NOT NULL,
                match_score REAL NOT NULL,
                tier TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )


def save_analysis(analysis: ResumeAnalysis) -> None:
    initialize_database()
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO analyses (
                analysis_id,
                created_at,
                candidate_name,
                source_filename,
                source_type,
                target_role,
                match_score,
                tier,
                payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis.analysis_id,
                analysis.created_at,
                analysis.candidate_name,
                analysis.source_filename,
                analysis.source_type,
                analysis.target_role,
                analysis.match_score,
                analysis.tier,
                analysis.model_dump_json(),
            ),
        )


def fetch_recent_analyses(limit: int = 20) -> list[HistoryEntry]:
    initialize_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT analysis_id, created_at, candidate_name, source_filename, source_type,
                   target_role, match_score, tier
            FROM analyses
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [HistoryEntry(**dict(row)) for row in rows]
