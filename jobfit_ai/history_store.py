from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

from jobfit_ai.models import HistoryEntry, ResumeAnalysis

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "jobfit_ai.db"


def get_connection() -> sqlite3.Connection:
    last_error: Exception | None = None
    for path in _candidate_db_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(path)
            connection.row_factory = sqlite3.Row
            return connection
        except OSError as exc:
            last_error = exc
        except sqlite3.Error as exc:
            last_error = exc

    raise RuntimeError("Unable to open a writable SQLite history database.") from last_error


def _candidate_db_paths() -> list[Path]:
    paths: list[Path] = []
    configured_path = os.getenv("JOBFIT_DB_PATH")
    if configured_path:
        paths.append(Path(configured_path).expanduser())

    paths.append(DB_PATH)
    paths.append(Path(tempfile.gettempdir()) / "jobfit-ai" / "jobfit_ai.db")

    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique_paths.append(path)
            seen.add(resolved)
    return unique_paths


def initialize_database() -> None:
    with closing(get_connection()) as connection:
        with connection:
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
    with closing(get_connection()) as connection:
        with connection:
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
                    json.dumps(asdict(analysis)),
                ),
            )


def fetch_recent_analyses(limit: int = 20) -> list[HistoryEntry]:
    initialize_database()
    with closing(get_connection()) as connection:
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
