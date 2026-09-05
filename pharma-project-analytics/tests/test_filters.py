"""Unit tests for src/filters.py."""

from __future__ import annotations

import pandas as pd
import pytest

from src.filters import FilterSelection, apply_filters


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Medicine_Name": "Paracetamol 500mg",
                "Category": "Analgesic",
                "Warehouse": "WH-North",
                "Expiry_Status": "SAFE",
                "Stock_Status": "NORMAL",
                "Risk_Level": "Low",
            },
            {
                "Medicine_Name": "Amoxicillin 250mg",
                "Category": "Antibiotic",
                "Warehouse": "WH-South",
                "Expiry_Status": "EXPIRED",
                "Stock_Status": "LOW_STOCK",
                "Risk_Level": "Critical",
            },
            {
                "Medicine_Name": "Insulin Glargine",
                "Category": "Hormone",
                "Warehouse": "WH-North",
                "Expiry_Status": "EXPIRING_SOON",
                "Stock_Status": "OVERSTOCK",
                "Risk_Level": "Medium",
            },
        ]
    )


class TestApplyFilters:
    def test_empty_selection_returns_all_rows(self, sample_df):
        result = apply_filters(sample_df, FilterSelection())
        assert len(result) == 3

    def test_single_field_filter(self, sample_df):
        result = apply_filters(sample_df, FilterSelection(categories=["Antibiotic"]))
        assert list(result["Medicine_Name"]) == ["Amoxicillin 250mg"]

    def test_multi_value_single_field(self, sample_df):
        result = apply_filters(
            sample_df, FilterSelection(risk_levels=["Critical", "Medium"])
        )
        assert len(result) == 2
        assert set(result["Risk_Level"]) == {"Critical", "Medium"}

    def test_combined_fields_and_together(self, sample_df):
        result = apply_filters(
            sample_df,
            FilterSelection(warehouses=["WH-North"], expiry_statuses=["SAFE"]),
        )
        assert list(result["Medicine_Name"]) == ["Paracetamol 500mg"]

    def test_no_match_returns_empty(self, sample_df):
        result = apply_filters(sample_df, FilterSelection(categories=["Nonexistent"]))
        assert result.empty

    def test_each_field_independently(self, sample_df):
        assert len(apply_filters(sample_df, FilterSelection(medicines=["Insulin Glargine"]))) == 1
        assert len(apply_filters(sample_df, FilterSelection(stock_statuses=["OVERSTOCK"]))) == 1
        assert len(apply_filters(sample_df, FilterSelection(warehouses=["WH-South"]))) == 1
