"""Unit tests for src/analytics.py.

Uses a small, hand-built DataFrame shaped like risk_engine.apply_risk_engine()
output (no dependency on the real dataset or on running the risk engine).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src import analytics


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


class TestRiskLevelCounts:
    def test_counts_each_level(self, enriched_df):
        counts = analytics.risk_level_counts(enriched_df).to_dict()
        assert counts == {"Critical": 1, "High": 1, "Low": 1, "Medium": 1}


class TestInventoryValueByCategory:
    def test_sums_excluding_nan(self, enriched_df):
        result = analytics.inventory_value_by_category(enriched_df)
        assert result["Analgesic"] == 500.0
        assert result["Antibiotic"] == 1000.0


class TestTotalInventoryValueAtRisk:
    def test_default_critical_and_high(self, enriched_df):
        assert analytics.total_inventory_value_at_risk(enriched_df) == 500.0

    def test_custom_risk_levels(self, enriched_df):
        assert analytics.total_inventory_value_at_risk(enriched_df, risk_levels=("Low",)) == 1000.0

    def test_level_with_only_nan_value_is_zero(self, enriched_df):
        assert analytics.total_inventory_value_at_risk(enriched_df, risk_levels=("Medium",)) == 0.0


class TestExpiringSoonItems:
    def test_includes_expired_and_expiring_soon_only(self, enriched_df):
        result = analytics.expiring_soon_items(enriched_df)
        assert list(result["Batch_ID"]) == ["BATCH-A", "BATCH-B"]

    def test_sorted_soonest_first(self, enriched_df):
        result = analytics.expiring_soon_items(enriched_df)
        assert list(result["Days_To_Expiry"]) == [-5, 10]


class TestLowStockItems:
    def test_returns_only_low_stock(self, enriched_df):
        result = analytics.low_stock_items(enriched_df)
        assert list(result["Batch_ID"]) == ["BATCH-A"]


class TestOverstockItems:
    def test_returns_only_overstock(self, enriched_df):
        result = analytics.overstock_items(enriched_df)
        assert list(result["Batch_ID"]) == ["BATCH-C"]


class TestCriticalMedicineSummary:
    def test_filters_to_critical_medicine_only(self, enriched_df):
        result = analytics.critical_medicine_summary(enriched_df)
        levels = dict(zip(result["Risk_Level"], result["Batch_Count"]))
        assert levels == {"Critical": 1, "Medium": 1}


class TestWarehouseSummary:
    def test_batch_count_and_total_value(self, enriched_df):
        result = analytics.warehouse_summary(enriched_df)
        assert result.loc["WH-North", "Batch_Count"] == 2
        assert result.loc["WH-North", "Total_Inventory_Value"] == 500.0
        assert result.loc["WH-South", "Batch_Count"] == 2
        assert result.loc["WH-South", "Total_Inventory_Value"] == 1000.0
