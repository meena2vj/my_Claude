"""Validate, sanitize, and load an uploaded CSV/XLSX file.

The only place raw upload bytes are trusted from: extension allowlist, size
cap, filename sanitization, and safe-path storage all happen here before any
`pandas.read_*` call.
"""

import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from config.settings import ALLOWED_DATA_EXTENSIONS, MAX_UPLOAD_FILE_SIZE_MB, UPLOAD_DIR
from graph.state import RawDataMeta


class FileValidationError(Exception):
    """Raised when an uploaded file fails validation. Safe to show to the user."""


@dataclass
class ValidatedFile:
    path: Path
    original_filename: str
    size_bytes: int
    extension: str


def sanitize_filename(filename: str) -> str:
    name = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    name = name.strip("._") or "upload"
    return name[:200]


def validate_and_save(
    uploaded_file,
    *,
    allowed_extensions: tuple[str, ...] = ALLOWED_DATA_EXTENSIONS,
    max_size_mb: int = MAX_UPLOAD_FILE_SIZE_MB,
    dest_dir: Path = UPLOAD_DIR,
) -> ValidatedFile:
    """`uploaded_file` is a Streamlit `UploadedFile` (has `.name` and `.getvalue()`)."""
    filename = uploaded_file.name
    extension = Path(filename).suffix.lower()
    if extension not in allowed_extensions:
        raise FileValidationError(
            f"Unsupported file type '{extension or '(none)'}'. "
            f"Allowed: {', '.join(allowed_extensions)}"
        )

    data = uploaded_file.getvalue()
    size_bytes = len(data)
    if size_bytes == 0:
        raise FileValidationError("Uploaded file is empty.")
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise FileValidationError(
            f"File exceeds the {max_size_mb} MB limit "
            f"({size_bytes / (1024 * 1024):.1f} MB)."
        )

    safe_name = sanitize_filename(filename)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{uuid.uuid4().hex}_{safe_name}"
    dest_path.write_bytes(data)

    return ValidatedFile(
        path=dest_path, original_filename=filename, size_bytes=size_bytes, extension=extension
    )


def load_dataframe(validated: ValidatedFile) -> tuple[pd.DataFrame, RawDataMeta]:
    try:
        if validated.extension == ".csv":
            df = pd.read_csv(validated.path)
        else:
            df = pd.read_excel(validated.path)
    except Exception as exc:  # noqa: BLE001 - surface as a validation error, not a crash
        raise FileValidationError(f"Could not parse '{validated.original_filename}': {exc}") from exc

    if df.empty:
        raise FileValidationError(f"'{validated.original_filename}' contains no rows.")

    meta = RawDataMeta(
        filename=validated.original_filename,
        upload_ts=datetime.now(timezone.utc).isoformat(),
        rows=len(df),
        columns=len(df.columns),
        dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
    )
    return df, meta
