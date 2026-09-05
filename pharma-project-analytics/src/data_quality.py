"""Data quality checks for the pharma inventory dataset.

Implements the data-quality dimensions required for Phase 2: missing
values, duplicate records (both exact-row duplicates and duplicate
Batch_ID with conflicting data), invalid dates, and negative stock
values. Every check only *detects and reports* issues — per
docs/GOVERNANCE.md ("never attempt to 'guess' or silently repair
malformed data"), nothing here mutates or drops rows from the input
DataFrame.

Duplicate detection is split into two distinct checks because they
represent different problems: `check_duplicate_rows` finds rows that
are identical in every column (an accidental double-entry of the same
data), while `check_duplicate_batch_ids` finds rows that share a
Batch_ID but *disagree* on other fields (a worse integrity problem,
since Batch_ID is meant to be a unique key and it is then ambiguous
which row is authoritative).

Row indices referenced in the report are the DataFrame's index labels
(as loaded by `data_loader.load_inventory_csv`, this is the 0-based row
position in the source file).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .parsing import is_blank, to_date, to_float

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

DATE_COLUMNS = ["Manufacturing_Date", "Expiry_Date"]


@dataclass
class DataQualityReport:
    """Structured result of running all data-quality checks on a DataFrame."""

    total_rows: int
    missing_by_column: dict[str, list[int]] = field(default_factory=dict)
    duplicate_row_groups: list[list[int]] = field(default_factory=list)
    duplicate_batch_id_groups: dict[str, list[int]] = field(default_factory=dict)
    invalid_date_rows: dict[int, list[str]] = field(default_factory=dict)
    negative_stock_rows: list[int] = field(default_factory=list)

    def missing_value_counts(self) -> dict[str, int]:
        return {col: len(rows) for col, rows in self.missing_by_column.items() if rows}

    def has_issues(self) -> bool:
        return bool(
            self.missing_value_counts()
            or self.duplicate_row_groups
            or self.duplicate_batch_id_groups
            or self.invalid_date_rows
            or self.negative_stock_rows
        )

    def summary(self) -> dict:
        """A compact, JSON-serialisable summary for reporting/logging."""
        return {
            "total_rows": self.total_rows,
            "missing_value_counts": self.missing_value_counts(),
            "duplicate_row_count": sum(len(g) for g in self.duplicate_row_groups),
            "duplicate_group_count": len(self.duplicate_row_groups),
            "duplicate_batch_id_row_count": sum(
                len(rows) for rows in self.duplicate_batch_id_groups.values()
            ),
            "duplicate_batch_id_group_count": len(self.duplicate_batch_id_groups),
            "invalid_date_row_count": len(self.invalid_date_rows),
            "negative_stock_row_count": len(self.negative_stock_rows),
        }


def check_missing_values(
    df: pd.DataFrame, columns: list[str] | None = None
) -> dict[str, list[int]]:
    """Return {column: [row indices]} for every required column that has a
    blank/NaN cell. Columns with no missing values are omitted.
    """
    columns = columns if columns is not None else REQUIRED_COLUMNS
    missing: dict[str, list[int]] = {}
    for col in columns:
        if col not in df.columns:
            continue
        rows = [idx for idx, value in df[col].items() if is_blank(value)]
        if rows:
            missing[col] = rows
    return missing


def check_duplicate_rows(df: pd.DataFrame) -> list[list[int]]:
    """Return groups of row indices that are exact duplicates of each other
    across every column (e.g. an accidental double-entry of the same
    batch). Rows with no duplicate are not included.
    """
    if df.empty:
        return []

    dup_mask = df.duplicated(keep=False)
    if not dup_mask.any():
        return []

    groups: dict[tuple, list[int]] = {}
    for idx, row in df[dup_mask].iterrows():
        key = tuple(None if is_blank(v) else v for v in row.tolist())
        groups.setdefault(key, []).append(idx)

    return [rows for rows in groups.values() if len(rows) > 1]


def check_duplicate_batch_ids(df: pd.DataFrame) -> dict[str, list[int]]:
    """Return {Batch_ID: [row indices]} for every non-blank Batch_ID that
    appears on more than one row - regardless of whether the rest of the
    row matches (an exact full-row duplicate is also caught here, since
    it necessarily shares its Batch_ID; a Batch_ID reused with
    *different* other data is caught here but not by
    `check_duplicate_rows`).
    """
    if "Batch_ID" not in df.columns:
        return {}

    groups: dict[str, list[int]] = {}
    for idx, raw in df["Batch_ID"].items():
        if is_blank(raw):
            continue
        groups.setdefault(str(raw), []).append(idx)

    return {batch_id: rows for batch_id, rows in groups.items() if len(rows) > 1}


def check_invalid_dates(df: pd.DataFrame) -> dict[int, list[str]]:
    """Return {row index: [issue descriptions]} for rows where a date
    column is present but unparseable, or where Manufacturing_Date is
    after Expiry_Date (a logically invalid batch history).
    """
    issues: dict[int, list[str]] = {}

    for idx, row in df.iterrows():
        row_issues: list[str] = []
        parsed: dict[str, object] = {}

        for col in DATE_COLUMNS:
            raw = row.get(col)
            if is_blank(raw):
                continue
            value = to_date(raw)
            parsed[col] = value
            if value is None:
                row_issues.append(f"{col}: unparseable value '{raw}'")

        mfg = parsed.get("Manufacturing_Date")
        exp = parsed.get("Expiry_Date")
        if mfg is not None and exp is not None and mfg > exp:
            row_issues.append(
                f"Manufacturing_Date ({mfg}) is after Expiry_Date ({exp})"
            )

        if row_issues:
            issues[idx] = row_issues

    return issues


def check_negative_stock(df: pd.DataFrame) -> list[int]:
    """Return row indices where Current_Stock parses to a negative number."""
    rows = []
    for idx, raw in df.get("Current_Stock", pd.Series(dtype=object)).items():
        value = to_float(raw)
        if value is not None and value < 0:
            rows.append(idx)
    return rows


def run_data_quality_checks(df: pd.DataFrame) -> DataQualityReport:
    """Run all data-quality checks and return a combined report."""
    return DataQualityReport(
        total_rows=len(df),
        missing_by_column=check_missing_values(df),
        duplicate_row_groups=check_duplicate_rows(df),
        duplicate_batch_id_groups=check_duplicate_batch_ids(df),
        invalid_date_rows=check_invalid_dates(df),
        negative_stock_rows=check_negative_stock(df),
    )
