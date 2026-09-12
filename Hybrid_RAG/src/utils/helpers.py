"""Small reusable helpers: token approximation, text cleaning, timing, audit logging."""

import json
import os
import re
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

from config import AUDIT_LOG_PATH


def count_tokens_approx(text: str) -> int:
    """Lightweight word-level tokenizer approximation.

    Used everywhere a real model tokenizer is unavailable/unnecessary.
    """
    if not text:
        return 0
    return len(text.split())


def clean_text(text: str) -> str:
    """Normalize whitespace and strip control characters from extracted PDF text."""
    if not text:
        return ""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tokenize_words(text: str) -> list[str]:
    """Lowercase alphanumeric-word tokenizer shared by BM25 and grounding checks."""
    if not text:
        return []
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass
class Timer:
    """Context manager that records elapsed wall-clock time in seconds."""

    elapsed_seconds: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info) -> None:
        self.elapsed_seconds = time.perf_counter() - self._start


@contextmanager
def timed():
    """Usage: with timed() as t: ... ; t.elapsed_seconds"""
    timer = Timer()
    timer.__enter__()
    try:
        yield timer
    finally:
        timer.__exit__()


@dataclass
class AuditEvent:
    event_type: str
    payload: dict = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def audit_log(event_type: str, payload: dict | None = None, log_path: str = AUDIT_LOG_PATH) -> None:
    """Append a single JSON-line audit event. Never raises — logging must not break the app."""
    event = AuditEvent(event_type=event_type, payload=payload or {})
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.__dict__, default=str) + "\n")
    except Exception:
        pass


def read_audit_log(log_path: str = AUDIT_LOG_PATH, limit: int = 50) -> list[dict]:
    """Return the most recent `limit` audit events, newest last. Never raises."""
    if not os.path.exists(log_path):
        return []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
    except Exception:
        return []
