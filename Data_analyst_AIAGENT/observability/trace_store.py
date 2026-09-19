"""SQLite trace log -- one row per node/LLM/tool event, matching CLAUDE.md
section 14's field list (trace id, timestamp, node, LLM/tool call, input,
output, data transformation, latency, status). This is the backing store for
the Streamlit Observability & Traceability tab.
"""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from config.settings import TRACE_DB_PATH

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trace_events (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    node TEXT NOT NULL,
    event_type TEXT NOT NULL,
    user_question TEXT,
    llm_model TEXT,
    llm_prompt_tokens INTEGER,
    llm_completion_tokens INTEGER,
    tool_name TEXT,
    input_summary TEXT,
    output_summary TEXT,
    data_transformation TEXT,
    latency_seconds REAL,
    status TEXT NOT NULL,
    error_message TEXT
)
"""


@contextmanager
def _connect():
    TRACE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TRACE_DB_PATH)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def log_event(
    *,
    trace_id: str,
    node: str,
    event_type: str,
    status: str,
    user_question: str | None = None,
    llm_model: str | None = None,
    llm_prompt_tokens: int | None = None,
    llm_completion_tokens: int | None = None,
    tool_name: str | None = None,
    input_summary: str | None = None,
    output_summary: str | None = None,
    data_transformation: str | None = None,
    latency_seconds: float | None = None,
    error_message: str | None = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO trace_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                str(uuid.uuid4()),
                trace_id,
                datetime.now(timezone.utc).isoformat(),
                node,
                event_type,
                user_question,
                llm_model,
                llm_prompt_tokens,
                llm_completion_tokens,
                tool_name,
                input_summary,
                output_summary,
                data_transformation,
                latency_seconds,
                status,
                error_message,
            ),
        )


def fetch_events_for_trace(trace_id: str) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM trace_events WHERE trace_id = ? ORDER BY ts", (trace_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def fetch_recent_traces(limit: int = 20) -> list[dict]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT trace_id, MIN(ts) AS started_at, COUNT(*) AS event_count, "
            "SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS error_count "
            "FROM trace_events GROUP BY trace_id ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
