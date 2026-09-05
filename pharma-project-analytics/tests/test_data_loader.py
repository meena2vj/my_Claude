"""Unit tests for src/data_loader.py.

Uses pytest's `tmp_path` fixture for all file-based tests - no real
project files, no network. Covers file validation (extension, size,
existence) and CSV/column validation, per docs/GOVERNANCE.md
"File Validation".
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import (
    REQUIRED_COLUMNS,
    DataValidationError,
    load_inventory_csv,
    validate_columns,
    validate_file,
)

VALID_ROW = {
    "Batch_ID": "BATCH-0001",
    "Medicine_Name": "Paracetamol 500mg",
    "Category": "Analgesic",
    "Manufacturer": "MediCore Pharma",
    "Manufacturing_Date": "2025-01-01",
    "Expiry_Date": "2027-01-01",
    "Current_Stock": "100",
    "Reorder_Level": "50",
    "Maximum_Stock": "300",
    "Unit_Price": "5.0",
    "Warehouse": "WH-North",
    "Critical_Medicine": "No",
}


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    path.write_text("\n".join(lines) + "\n")
    return path


class TestValidateFile:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(DataValidationError, match="not found"):
            validate_file(tmp_path / "does_not_exist.csv")

    def test_directory_raises(self, tmp_path):
        with pytest.raises(DataValidationError, match="Not a file"):
            validate_file(tmp_path)

    def test_wrong_extension_raises(self, tmp_path):
        bad_file = tmp_path / "data.txt"
        bad_file.write_text("Batch_ID\n1\n")
        with pytest.raises(DataValidationError, match="Unsupported file type"):
            validate_file(bad_file)

    def test_oversized_file_raises(self, tmp_path):
        big_file = tmp_path / "big.csv"
        big_file.write_text("a" * 2000)
        with pytest.raises(DataValidationError, match="too large"):
            validate_file(big_file, max_size_mb=0.001)

    def test_valid_csv_returns_path(self, tmp_path):
        csv_file = tmp_path / "ok.csv"
        csv_file.write_text("Batch_ID\n1\n")
        result = validate_file(csv_file)
        assert result == csv_file


class TestValidateColumns:
    def test_all_required_columns_present_passes(self):
        df = pd.DataFrame([VALID_ROW])
        validate_columns(df)  # should not raise

    def test_missing_column_raises(self):
        df = pd.DataFrame([VALID_ROW]).drop(columns=["Warehouse"])
        with pytest.raises(DataValidationError, match="Warehouse"):
            validate_columns(df)


class TestLoadInventoryCsv:
    def test_loads_valid_file_with_expected_columns(self, tmp_path):
        csv_file = write_csv(
            tmp_path / "inventory.csv",
            list(VALID_ROW.keys()),
            [list(VALID_ROW.values())],
        )
        df = load_inventory_csv(csv_file)
        assert list(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 1
        assert df.iloc[0]["Batch_ID"] == "BATCH-0001"

    def test_drops_extra_columns(self, tmp_path):
        header = list(VALID_ROW.keys()) + ["Patient_Notes"]
        row = list(VALID_ROW.values()) + ["should be dropped"]
        csv_file = write_csv(tmp_path / "inventory.csv", header, [row])
        df = load_inventory_csv(csv_file)
        assert "Patient_Notes" not in df.columns
        assert list(df.columns) == REQUIRED_COLUMNS

    def test_missing_required_column_raises(self, tmp_path):
        header = [c for c in VALID_ROW if c != "Critical_Medicine"]
        row = [VALID_ROW[c] for c in header]
        csv_file = write_csv(tmp_path / "inventory.csv", header, [row])
        with pytest.raises(DataValidationError, match="Missing required column"):
            load_inventory_csv(csv_file)

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(DataValidationError):
            load_inventory_csv(tmp_path / "missing.csv")

    def test_malformed_csv_raises(self, tmp_path):
        # An unterminated quoted field is unambiguously malformed CSV and
        # reliably raises pandas.errors.ParserError ("EOF inside string").
        csv_file = tmp_path / "broken.csv"
        header = ",".join(VALID_ROW.keys())
        csv_file.write_text(f'{header}\n"unterminated,quote,field\n')
        with pytest.raises(DataValidationError, match="Could not parse"):
            load_inventory_csv(csv_file)
