"""Unit tests for src/report_generator.py."""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_quality import DataQualityReport
from src.report_generator import generate_markdown_report, generate_summary_report


@pytest.fixture
def enriched_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Batch_ID": "BATCH-A",
                "Category": "Analgesic",
                "Warehouse": "WH-North",
                "Critical_Medicine": "Yes",
                "Expiry_Status": "EXPIRED",
                "Stock_Status": "LOW_STOCK",
                "Days_To_Expiry": -5,
                "Current_Stock": 10,
                "Inventory_Value": 100.0,
                "Risk_Level": "Critical",
            },
            {
                "Batch_ID": "BATCH-B",
                "Category": "Analgesic",
                "Warehouse": "WH-North",
                "Critical_Medicine": "No",
                "Expiry_Status": "EXPIRING_SOON",
                "Stock_Status": "NORMAL",
                "Days_To_Expiry": 10,
                "Current_Stock": 200,
                "Inventory_Value": 400.0,
                "Risk_Level": "High",
            },
            {
                "Batch_ID": "BATCH-C",
                "Category": "Antibiotic",
                "Warehouse": "WH-South",
                "Critical_Medicine": "No",
                "Expiry_Status": "SAFE",
                "Stock_Status": "OVERSTOCK",
                "Days_To_Expiry": 100,
                "Current_Stock": 500,
                "Inventory_Value": 1000.0,
                "Risk_Level": "Low",
            },
            {
                "Batch_ID": "BATCH-D",
                "Category": "Antibiotic",
                "Warehouse": "WH-South",
                "Critical_Medicine": "Yes",
                "Expiry_Status": "SAFE",
                "Stock_Status": "NORMAL",
                "Days_To_Expiry": 200,
                "Current_Stock": 150,
                "Inventory_Value": float("nan"),
                "Risk_Level": "Medium",
            },
        ]
    )


class TestGenerateSummaryReport:
    def test_basic_counts(self, enriched_df):
        report = generate_summary_report(enriched_df)
        assert report["total_batches"] == 4
        assert report["risk_level_counts"] == {"Critical": 1, "High": 1, "Low": 1, "Medium": 1}
        assert report["total_inventory_value_at_risk"] == 500.0
        assert report["expiring_soon_count"] == 2
        assert report["low_stock_count"] == 1
        assert report["overstock_count"] == 1
        assert report["critical_risk_batch_ids"] == ["BATCH-A"]

    def test_without_quality_report_omits_data_quality_key(self, enriched_df):
        report = generate_summary_report(enriched_df)
        assert "data_quality" not in report

    def test_with_quality_report_includes_summary(self, enriched_df):
        quality_report = DataQualityReport(
            total_rows=4,
            missing_by_column={"Manufacturer": [2]},
            duplicate_row_groups=[[0, 1]],
            invalid_date_rows={},
            negative_stock_rows=[],
        )
        report = generate_summary_report(enriched_df, quality_report)
        assert report["data_quality"]["total_rows"] == 4
        assert report["data_quality"]["missing_value_counts"] == {"Manufacturer": 1}
        assert report["data_quality"]["duplicate_row_count"] == 2


class TestGenerateMarkdownReport:
    def test_contains_risk_level_breakdown(self, enriched_df):
        markdown = generate_markdown_report(enriched_df)
        assert "# Pharma Inventory Risk Summary" in markdown
        assert "Critical: 1" in markdown
        assert "High: 1" in markdown

    def test_contains_critical_batch_for_human_review(self, enriched_df):
        markdown = generate_markdown_report(enriched_df)
        assert "Critical Risk - Requires Human Review" in markdown
        assert "BATCH-A" in markdown

    def test_no_critical_batches_shows_none(self):
        df = pd.DataFrame(
            [
                {
                    "Batch_ID": "BATCH-X",
                    "Expiry_Status": "SAFE",
                    "Stock_Status": "NORMAL",
                    "Days_To_Expiry": 100,
                    "Current_Stock": 50,
                    "Inventory_Value": 10.0,
                    "Risk_Level": "Low",
                }
            ]
        )
        markdown = generate_markdown_report(df)
        assert "- None" in markdown

    def test_omits_data_quality_section_when_not_provided(self, enriched_df):
        markdown = generate_markdown_report(enriched_df)
        assert "## Data Quality" not in markdown

    def test_includes_data_quality_section_when_provided(self, enriched_df):
        quality_report = DataQualityReport(total_rows=4)
        markdown = generate_markdown_report(enriched_df, quality_report)
        assert "## Data Quality" in markdown
