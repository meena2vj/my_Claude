"""Small reusable helpers: token approximation, text cleaning, timing."""

import re
import time
from contextlib import contextmanager
from dataclasses import dataclass


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
