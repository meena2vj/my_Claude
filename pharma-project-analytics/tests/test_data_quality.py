"""Unit tests for src/data_quality.py.

All tests use in-memory DataFrames only - no real files, no network, no
system time dependency (data_quality has no time-based logic).
"""

from __future__ import annotations

import pandas as pd

from src.data_quality import (
    DataQualityReport,
    check_duplicate_batch_ids,
    check_duplicate_rows,
    check_invalid_dates,
    check_missing_values,
    check_negative_stock,
    run_data_quality_checks,
)


def make_row(**overrides) -> dict:
    row = {
        "Batch_ID": "BATCH-0001",
        "Medicine_Name": "Paracetamol 500mg",
        "Category": "Analgesic",
        "Manufacturer": "MediCore Pharma",
        "Manufacturing_Date": "2025-01-01",
        "Expiry_Date": "2027-01-01",
        "Current_Stock": 100,
        "Reorder_Level": 50,
        "Maximum_Stock": 300,
        "Unit_Price": 5.0,
        "Warehouse": "WH-North",
        "Critical_Medicine": "No",
    }
    row.update(overrides)
    return row


class TestCheckMissingValues:
    def test_no_missing_values_returns_empty(self):
        df = pd.DataFrame([make_row(), make_row(Batch_ID="BATCH-0002")])
        assert check_missing_values(df) == {}

    def test_blank_string_is_missing(self):
        df = pd.DataFrame([make_row(Medicine_Name="")])
        result = check_missing_values(df)
        assert result == {"Medicine_Name": [0]}

    def test_nan_is_missing(self):
        df = pd.DataFrame([make_row(Unit_Price=float("nan"))])
        result = check_missing_values(df)
        assert result == {"Unit_Price": [0]}

    def test_multiple_rows_and_columns(self):
        df = pd.DataFrame(
            [make_row(Warehouse=""), make_row(Warehouse="", Category="")]
        )
        result = check_missing_values(df)
        assert result["Warehouse"] == [0, 1]
        assert result["Category"] == [1]


class TestCheckDuplicateRows:
    def test_no_duplicates(self):
        df = pd.DataFrame([make_row(Batch_ID="BATCH-0001"), make_row(Batch_ID="BATCH-0002")])
        assert check_duplicate_rows(df) == []

    def test_exact_duplicate_pair_detected(self):
        df = pd.DataFrame([make_row(), make_row()])
        groups = check_duplicate_rows(df)
        assert groups == [[0, 1]]

    def test_partial_difference_is_not_a_duplicate(self):
        df = pd.DataFrame([make_row(Current_Stock=100), make_row(Current_Stock=101)])
        assert check_duplicate_rows(df) == []

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=list(make_row().keys()))
        assert check_duplicate_rows(df) == []

    def test_three_way_duplicate_group(self):
        df = pd.DataFrame([make_row(), make_row(), make_row(Batch_ID="BATCH-0002")])
        groups = check_duplicate_rows(df)
        assert groups == [[0, 1]]


class TestCheckDuplicateBatchIds:
    def test_unique_batch_ids_not_flagged(self):
        df = pd.DataFrame([make_row(Batch_ID="BATCH-0001"), make_row(Batch_ID="BATCH-0002")])
        assert check_duplicate_batch_ids(df) == {}

    def test_same_batch_id_conflicting_data_is_flagged(self):
        df = pd.DataFrame(
            [
                make_row(Batch_ID="BATCH-0001", Current_Stock=100),
                make_row(Batch_ID="BATCH-0001", Current_Stock=999, Warehouse="WH-South"),
            ]
        )
        result = check_duplicate_batch_ids(df)
        assert result == {"BATCH-0001": [0, 1]}

    def test_exact_duplicate_row_is_also_a_duplicate_batch_id(self):
        df = pd.DataFrame([make_row(), make_row()])
        result = check_duplicate_batch_ids(df)
        assert result == {"BATCH-0001": [0, 1]}

    def test_blank_batch_id_not_flagged(self):
        df = pd.DataFrame([make_row(Batch_ID=""), make_row(Batch_ID="")])
        assert check_duplicate_batch_ids(df) == {}

    def test_three_rows_same_batch_id(self):
        df = pd.DataFrame(
            [
                make_row(Batch_ID="BATCH-0001", Current_Stock=1),
                make_row(Batch_ID="BATCH-0001", Current_Stock=2),
                make_row(Batch_ID="BATCH-0001", Current_Stock=3),
            ]
        )
        result = check_duplicate_batch_ids(df)
        assert result == {"BATCH-0001": [0, 1, 2]}


class TestCheckInvalidDates:
    def test_valid_dates_no_issue(self):
        df = pd.DataFrame([make_row()])
        assert check_invalid_dates(df) == {}

    def test_unparseable_expiry_date_flagged(self):
        df = pd.DataFrame([make_row(Expiry_Date="not-a-date")])
        result = check_invalid_dates(df)
        assert 0 in result
        assert any("Expiry_Date" in issue for issue in result[0])

    def test_unparseable_manufacturing_date_flagged(self):
        df = pd.DataFrame([make_row(Manufacturing_Date="31/02/2026")])
        result = check_invalid_dates(df)
        assert 0 in result

    def test_manufacturing_after_expiry_flagged(self):
        df = pd.DataFrame(
            [make_row(Manufacturing_Date="2027-06-01", Expiry_Date="2027-01-01")]
        )
        result = check_invalid_dates(df)
        assert 0 in result
        assert any("after" in issue for issue in result[0])

    def test_missing_date_is_not_an_invalid_date_issue(self):
        df = pd.DataFrame([make_row(Expiry_Date="")])
        assert check_invalid_dates(df) == {}


class TestCheckNegativeStock:
    def test_positive_stock_not_flagged(self):
        df = pd.DataFrame([make_row(Current_Stock=10)])
        assert check_negative_stock(df) == []

    def test_zero_stock_not_flagged(self):
        df = pd.DataFrame([make_row(Current_Stock=0)])
        assert check_negative_stock(df) == []

    def test_negative_stock_flagged(self):
        df = pd.DataFrame([make_row(Current_Stock=-5)])
        assert check_negative_stock(df) == [0]

    def test_non_numeric_stock_not_flagged_here(self):
        df = pd.DataFrame([make_row(Current_Stock="not_a_number")])
        assert check_negative_stock(df) == []

    def test_missing_stock_not_flagged_here(self):
        df = pd.DataFrame([make_row(Current_Stock="")])
        assert check_negative_stock(df) == []


class TestRunDataQualityChecks:
    def test_clean_dataframe_has_no_issues(self):
        df = pd.DataFrame([make_row(Batch_ID="BATCH-0001"), make_row(Batch_ID="BATCH-0002")])
        report = run_data_quality_checks(df)
        assert isinstance(report, DataQualityReport)
        assert report.total_rows == 2
        assert report.has_issues() is False

    def test_report_aggregates_all_dimensions(self):
        df = pd.DataFrame(
            [
                make_row(Batch_ID="BATCH-0001", Current_Stock=-5),
                make_row(Batch_ID="BATCH-0002", Expiry_Date="not-a-date"),
                make_row(Batch_ID="BATCH-0003", Manufacturer=""),
                make_row(Batch_ID="BATCH-0004"),
                make_row(Batch_ID="BATCH-0004"),
            ]
        )
        report = run_data_quality_checks(df)
        assert report.total_rows == 5
        assert report.has_issues() is True
        assert report.negative_stock_rows == [0]
        assert 1 in report.invalid_date_rows
        assert report.missing_by_column.get("Manufacturer") == [2]
        assert report.duplicate_row_groups == [[3, 4]]
        assert report.duplicate_batch_id_groups == {"BATCH-0004": [3, 4]}

        summary = report.summary()
        assert summary["total_rows"] == 5
        assert summary["negative_stock_row_count"] == 1
        assert summary["invalid_date_row_count"] == 1
        assert summary["duplicate_row_count"] == 2
        assert summary["duplicate_group_count"] == 1
        assert summary["duplicate_batch_id_row_count"] == 2
        assert summary["duplicate_batch_id_group_count"] == 1
        assert summary["missing_value_counts"] == {"Manufacturer": 1}

    def test_duplicate_batch_id_with_conflicting_data_is_detected(self):
        df = pd.DataFrame(
            [
                make_row(Batch_ID="BATCH-0001", Current_Stock=100, Warehouse="WH-North"),
                make_row(Batch_ID="BATCH-0001", Current_Stock=999, Warehouse="WH-South"),
            ]
        )
        report = run_data_quality_checks(df)
        assert report.duplicate_row_groups == []
        assert report.duplicate_batch_id_groups == {"BATCH-0001": [0, 1]}
        assert report.has_issues() is True
