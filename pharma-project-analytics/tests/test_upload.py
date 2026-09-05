"""Unit tests for src/upload.py.

Uses in-memory `io.BytesIO` buffers (wrapped to expose `.name`/`.size`
like Streamlit's `UploadedFile`) for every case - no real files, no
network, matching CLAUDE.md's testing rule and docs/GOVERNANCE.md's
"Session-Only Processing" (uploads must never touch disk).
"""

from __future__ import annotations

import io

import pandas as pd
import pytest

from src.data_loader import DataValidationError, REQUIRED_COLUMNS
from src.upload import load_inventory_upload, validate_upload

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


class FakeUpload(io.BytesIO):
    """Minimal stand-in for Streamlit's UploadedFile: adds `.name`/`.size`
    on top of a plain in-memory buffer.
    """

    def __init__(self, data: bytes, name: str):
        super().__init__(data)
        self.name = name
        self.size = len(data)


def make_csv_upload(header: list[str], rows: list[list[str]], name: str = "inventory.csv") -> FakeUpload:
    lines = [",".join(header)]
    lines.extend(",".join(row) for row in rows)
    return FakeUpload(("\n".join(lines) + "\n").encode(), name)


def make_xlsx_upload(header: list[str], rows: list[list[str]], name: str = "inventory.xlsx") -> FakeUpload:
    df = pd.DataFrame(rows, columns=header)
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return FakeUpload(buf.getvalue(), name)


class TestValidateUpload:
    def test_valid_csv_passes(self):
        upload = make_csv_upload(list(VALID_ROW.keys()), [list(VALID_ROW.values())])
        validate_upload(upload)  # should not raise

    def test_unsupported_extension_raises(self):
        upload = FakeUpload(b"not a real file", "notes.txt")
        with pytest.raises(DataValidationError, match="Unsupported file type"):
            validate_upload(upload)

    def test_missing_name_raises(self):
        upload = FakeUpload(b"data", "")
        with pytest.raises(DataValidationError, match="no name"):
            validate_upload(upload)

    def test_oversized_file_raises(self):
        upload = FakeUpload(b"a" * 2000, "big.csv")
        with pytest.raises(DataValidationError, match="too large"):
            validate_upload(upload, max_size_mb=0.001)

    def test_xlsx_extension_passes(self):
        upload = make_xlsx_upload(list(VALID_ROW.keys()), [list(VALID_ROW.values())])
        validate_upload(upload)  # should not raise


class TestLoadInventoryUpload:
    def test_loads_valid_csv(self):
        upload = make_csv_upload(list(VALID_ROW.keys()), [list(VALID_ROW.values())])
        df = load_inventory_upload(upload)
        assert list(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 1
        assert df.iloc[0]["Batch_ID"] == "BATCH-0001"

    def test_loads_valid_xlsx(self):
        upload = make_xlsx_upload(list(VALID_ROW.keys()), [list(VALID_ROW.values())])
        df = load_inventory_upload(upload)
        assert list(df.columns) == REQUIRED_COLUMNS
        assert len(df) == 1
        assert df.iloc[0]["Batch_ID"] == "BATCH-0001"

    def test_drops_extra_columns(self):
        header = list(VALID_ROW.keys()) + ["Patient_Notes"]
        row = list(VALID_ROW.values()) + ["should be dropped"]
        upload = make_csv_upload(header, [row])
        df = load_inventory_upload(upload)
        assert "Patient_Notes" not in df.columns
        assert list(df.columns) == REQUIRED_COLUMNS

    def test_missing_required_column_raises(self):
        header = [c for c in VALID_ROW if c != "Critical_Medicine"]
        row = [VALID_ROW[c] for c in header]
        upload = make_csv_upload(header, [row])
        with pytest.raises(DataValidationError, match="Missing required column"):
            load_inventory_upload(upload)

    def test_wrong_extension_raises(self):
        upload = FakeUpload(b"Batch_ID\n1\n", "inventory.pdf")
        with pytest.raises(DataValidationError, match="Unsupported file type"):
            load_inventory_upload(upload)

    def test_malformed_csv_raises(self):
        header = ",".join(VALID_ROW.keys())
        upload = FakeUpload(f'{header}\n"unterminated,quote,field\n'.encode(), "broken.csv")
        with pytest.raises(DataValidationError, match="Could not parse"):
            load_inventory_upload(upload)

    def test_unparseable_xls_raises_data_validation_error(self):
        """A `.xls` extension is allowed, but openpyxl cannot open the
        legacy binary format and raises its own exception type on a real
        (or malformed) .xls file. That must surface as a clear
        DataValidationError, not an unhandled exception that would halt
        the whole dashboard.
        """
        upload = FakeUpload(b"not a real spreadsheet", "inventory.xls")
        with pytest.raises(DataValidationError, match="Could not parse"):
            load_inventory_upload(upload)
