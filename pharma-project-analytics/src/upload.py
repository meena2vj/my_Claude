"""In-memory validation and loading for user-uploaded inventory files.

Per docs/GOVERNANCE.md ("Session-Only Processing"): an uploaded file must
never be written to disk. This module validates and parses directly from
the in-memory buffer Streamlit hands us (or any file-like object exposing
`.name`, `.size`, and standard binary-read/seek methods), and never calls
anything that persists the upload.

Reuses `DataValidationError`, `REQUIRED_COLUMNS`, and `validate_columns`
from `src/data_loader.py` rather than duplicating them - `data_loader.py`
itself stays disk/CSV-only (used only for the bundled sample dataset).
"""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

import pandas as pd

from .data_loader import REQUIRED_COLUMNS, DataValidationError, validate_columns

ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".xlsx", ".xls"}
DEFAULT_MAX_SIZE_MB = 10.0


def validate_upload(uploaded_file: Any, max_size_mb: float = DEFAULT_MAX_SIZE_MB) -> None:
    """Validate an in-memory upload's name/extension and size.

    `uploaded_file` must expose `.name` (str) and `.size` (bytes, int).
    Raises DataValidationError on any failure; never touches disk.
    """
    name = getattr(uploaded_file, "name", None)
    if not name:
        raise DataValidationError("Uploaded file has no name.")

    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        raise DataValidationError(
            f"Unsupported file type '{suffix}'. "
            f"Allowed types: {sorted(ALLOWED_UPLOAD_EXTENSIONS)}"
        )

    size = getattr(uploaded_file, "size", None)
    if size is not None:
        size_mb = size / (1024 * 1024)
        if size_mb > max_size_mb:
            raise DataValidationError(
                f"File too large ({size_mb:.2f} MB). Maximum allowed is {max_size_mb} MB."
            )


def load_inventory_upload(
    uploaded_file: Any, max_size_mb: float = DEFAULT_MAX_SIZE_MB
) -> pd.DataFrame:
    """Validate and parse an uploaded CSV/Excel file entirely in memory.

    Returns a DataFrame containing exactly `REQUIRED_COLUMNS`, in that
    order, values read as strings (no coercion/repair - matches
    `data_loader.load_inventory_csv`). Any extra columns are dropped
    (data minimisation). Raises DataValidationError on any invalid
    file/extension/size/column/parse failure.
    """
    validate_upload(uploaded_file, max_size_mb=max_size_mb)

    name = uploaded_file.name
    suffix = PurePosixPath(name).suffix.lower()

    try:
        if suffix == ".csv":
            df = pd.read_csv(uploaded_file, dtype=str)
        else:
            df = pd.read_excel(uploaded_file, dtype=str, engine="openpyxl")
    except Exception as exc:
        # openpyxl raises its own exception types (e.g. for a legacy
        # binary .xls file it cannot open) that aren't pandas/stdlib
        # errors, so this is intentionally broad: any parse failure must
        # surface as a clear, specific rejection rather than an unhandled
        # exception that halts the whole dashboard.
        raise DataValidationError(f"Could not parse '{name}': {exc}") from exc

    validate_columns(df)
    return df[REQUIRED_COLUMNS].copy()
