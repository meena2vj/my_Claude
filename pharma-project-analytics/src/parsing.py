"""Safe, deterministic scalar parsing helpers shared by data_quality.py and
risk_engine.py.

Every function here returns `None` for missing, blank, or unparseable
input rather than raising or guessing a value — per docs/GOVERNANCE.md,
malformed data must be surfaced, never silently repaired.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pandas as pd


def is_blank(value: Any) -> bool:
    """True for NaN/None or a string that is empty/whitespace-only."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def to_float(value: Any) -> Optional[float]:
    """Parse a numeric cell. Returns None if blank or not a valid number."""
    if is_blank(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_date(value: Any) -> Optional[date]:
    """Parse a date cell (expected format YYYY-MM-DD, but any format
    pandas can unambiguously parse is accepted). Returns None if blank
    or not a valid calendar date.
    """
    if is_blank(value):
        return None
    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (ValueError, TypeError):
        return None
    return parsed.date()


def to_yes_no(value: Any) -> Optional[bool]:
    """Parse a Yes/No style flag. Returns None if blank or not one of the
    recognised values (never guesses True/False for an unrecognised
    string).
    """
    if is_blank(value):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"yes", "true", "1"}:
        return True
    if normalized in {"no", "false", "0"}:
        return False
    return None
