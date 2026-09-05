"""File validation and loading for the pharma inventory dataset.

Per docs/GOVERNANCE.md ("File Validation" and "Data Minimisation"):
uploaded/loaded files must be validated (extension, size, required
columns) before use, invalid files must be rejected with a clear message
rather than silently guessed or repaired, and only the columns required
for analytics are retained.

This module intentionally does no type coercion or cleanup of cell
values — it loads raw data. Detecting bad values (missing, invalid
dates, negative stock, duplicates) is the responsibility of
`data_quality.py`; interpreting them into risk classifications is the
responsibility of `risk_engine.py`.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    "Batch_ID",
    "Medicine_Name",
    "Category",
    "Manufacturer",
    "Manufacturing_Date",
    "Expiry_Date",
    "Current_Stock",
    "Reorder_Level",
    "Maximum_Stock",
    "Unit_Price",
    "Warehouse",
    "Critical_Medicine",
]

ALLOWED_EXTENSIONS = {".csv"}
DEFAULT_MAX_SIZE_MB = 10.0


class DataValidationError(ValueError):
    """Raised when an input file fails validation.

    Callers must surface this message to the user rather than attempting
    to guess or auto-repair the file (docs/GOVERNANCE.md: "Reject and
    clearly report invalid files; never attempt to 'guess' or silently
    repair malformed data.").
    """


def validate_file(path: str | Path, max_size_mb: float = DEFAULT_MAX_SIZE_MB) -> Path:
    """Validate that `path` exists, has an allowed extension, and is within
    the size limit. Returns the resolved Path on success.

    Raises DataValidationError on any failure.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise DataValidationError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise DataValidationError(f"Not a file: {file_path}")
    if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise DataValidationError(
            f"Unsupported file type '{file_path.suffix}'. "
            f"Allowed types: {sorted(ALLOWED_EXTENSIONS)}"
        )

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise DataValidationError(
            f"File too large ({size_mb:.2f} MB). Maximum allowed is {max_size_mb} MB."
        )

    return file_path


def validate_columns(df: pd.DataFrame) -> None:
    """Raise DataValidationError if any required column is missing."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise DataValidationError(
            f"Missing required column(s): {missing}. "
            f"Expected columns: {REQUIRED_COLUMNS}"
        )


def load_inventory_csv(
    path: str | Path, max_size_mb: float = DEFAULT_MAX_SIZE_MB
) -> pd.DataFrame:
    """Validate and load a pharma inventory CSV file.

    Returns a DataFrame containing exactly `REQUIRED_COLUMNS`, in that
    order, with values as read from the file (empty cells become NaN via
    pandas' default CSV parsing; no other coercion or repair is applied).
    Any columns beyond the required set are dropped (data minimisation).

    Raises DataValidationError if the file is missing, the wrong type,
    too large, unreadable as CSV, or missing a required column.
    """
    file_path = validate_file(path, max_size_mb=max_size_mb)

    try:
        df = pd.read_csv(file_path, dtype=str)
    except (pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise DataValidationError(f"Could not parse '{file_path}' as CSV: {exc}") from exc

    validate_columns(df)
    return df[REQUIRED_COLUMNS].copy()
