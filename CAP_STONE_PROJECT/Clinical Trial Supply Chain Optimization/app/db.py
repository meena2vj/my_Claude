"""SQLite persistence for run state and audit trail — CLAUDE.md §8, §14, §21."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "ip_runway.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    request_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    final_status TEXT NOT NULL,
    report_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS qa_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    grounded_on_request_ids TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    latency_ms REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mcp_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    site_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    requesting_scope TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(_SCHEMA)
    return conn


def save_run(request_id: str, site_id: str, final_status: str, report: dict) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO runs (request_id, site_id, final_status, report_json, created_at)
               VALUES (?, ?, ?, ?, datetime('now'))
               ON CONFLICT(request_id) DO UPDATE SET
                 final_status=excluded.final_status, report_json=excluded.report_json""",
            (request_id, site_id, final_status, json.dumps(report, default=str)),
        )
    conn.close()


def get_run(request_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT report_json FROM runs WHERE request_id = ?", (request_id,)).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def list_runs(limit: int = 50) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT report_json FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]


def save_qa(
    question: str,
    answer: str,
    grounded_on_request_ids: list[str],
    model: str,
    prompt_version: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    latency_ms: float,
) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO qa_log (
                   question, answer, grounded_on_request_ids,
                   model, prompt_version, prompt_tokens, completion_tokens, latency_ms,
                   created_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                question, answer, json.dumps(grounded_on_request_ids),
                model, prompt_version, prompt_tokens, completion_tokens, latency_ms,
            ),
        )
    conn.close()


def list_qa(limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT question, answer, grounded_on_request_ids, model, prompt_version, "
        "prompt_tokens, completion_tokens, latency_ms, created_at FROM qa_log "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "question": q,
            "answer": a,
            "grounded_on_request_ids": json.loads(g),
            "model": model,
            "prompt_version": prompt_version,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "created_at": c,
        }
        for q, a, g, model, prompt_version, prompt_tokens, completion_tokens, latency_ms, c in rows
    ]


def log_mcp_call(
    tool: str, site_id: str, source_id: str, requesting_scope: list[str], latency_ms: float
) -> None:
    conn = get_conn()
    with conn:
        conn.execute(
            """INSERT INTO mcp_calls (tool, site_id, source_id, requesting_scope, latency_ms, created_at)
               VALUES (?, ?, ?, ?, ?, datetime('now'))""",
            (tool, site_id, source_id, json.dumps(requesting_scope), latency_ms),
        )
    conn.close()


def list_mcp_calls(limit: int = 20) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT tool, site_id, source_id, requesting_scope, latency_ms, created_at FROM mcp_calls "
        "ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [
        {
            "tool": t,
            "site_id": s,
            "source_id": src,
            "requesting_scope": json.loads(scope),
            "latency_ms": latency_ms,
            "created_at": c,
        }
        for t, s, src, scope, latency_ms, c in rows
    ]
