"""Long-term chat/session memory -- SQLite, survives app restarts. There is
no login, so a generated `session_id` (shown in the sidebar) is the resume
key: paste it back into the Memory tab to browse or continue that session.
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from config.settings import MEMORY_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    label TEXT
);
CREATE TABLE IF NOT EXISTS turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    kpi_context TEXT,
    dataset_fingerprint TEXT
);
"""


@contextmanager
def _connect():
    MEMORY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MEMORY_DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def touch_session(session_id: str, label: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (session_id, created_at, last_seen_at, label) VALUES (?,?,?,?) "
            "ON CONFLICT(session_id) DO UPDATE SET last_seen_at = excluded.last_seen_at",
            (session_id, now, now, label),
        )


def save_turn(
    *,
    session_id: str,
    trace_id: str,
    role: str,
    content: str,
    kpi_context: str | None = None,
    dataset_fingerprint: str | None = None,
) -> None:
    touch_session(session_id)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO turns VALUES (?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                session_id,
                trace_id,
                datetime.now(timezone.utc).isoformat(),
                role,
                content,
                kpi_context,
                dataset_fingerprint,
            ),
        )


def fetch_relevant_turns(
    session_id: str, dataset_fingerprint: str | None = None, limit: int = 20
) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        if dataset_fingerprint:
            rows = conn.execute(
                "SELECT * FROM turns WHERE session_id = ? AND dataset_fingerprint = ? "
                "ORDER BY ts DESC LIMIT ?",
                (session_id, dataset_fingerprint, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY ts DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return list(reversed([dict(r) for r in rows]))


def list_sessions(limit: int = 50) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY last_seen_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def session_exists(session_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        return row is not None
