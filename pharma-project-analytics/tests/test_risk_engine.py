"""Unit tests for src/risk_engine.py.

All tests use a fixed reference date and in-memory DataFrames only - no
real files, no network, no system time drift (per CLAUDE.md testing
requirements). Boundary conditions (exactly 30 days to expiry, stock
exactly at reorder level / maximum stock) are explicitly covered.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.risk_engine import (
    EXPIRED,
    EXPIRING_SOON,
    EXPIRY_UNKNOWN,
    LOW_STOCK,
    NORMAL,
    OVERSTOCK,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    SAFE,
    STOCK_INVALID,
    STOCK_UNKNOWN,
    apply_risk_engine,
    classify_expiry_status,
    classify_risk_level,
    classify_stock_status,
    compute_days_to_expiry,
    compute_inventory_value,
    compute_risk_score,
    is_critical_risk,
    recommend_action,
)

REFERENCE_DATE = date(2026, 1, 1)


class TestComputeDaysToExpiry:
    def test_future_date(self):
        assert compute_days_to_expiry("2026-01-11", REFERENCE_DATE) == 10

    def test_past_date_is_negative(self):
        assert compute_days_to_expiry("2025-12-31", REFERENCE_DATE) == -1

    def test_same_day_is_zero(self):
        assert compute_days_to_expiry("2026-01-01", REFERENCE_DATE) == 0

    def test_missing_date_returns_none(self):
        assert compute_days_to_expiry("", REFERENCE_DATE) is None
        assert compute_days_to_expiry(None, REFERENCE_DATE) is None

    def test_invalid_date_returns_none(self):
        assert compute_days_to_expiry("not-a-date", REFERENCE_DATE) is None
        assert compute_days_to_expiry("2026-13-45", REFERENCE_DATE) is None


class TestClassifyExpiryStatus:
    def test_negative_days_is_expired(self):
        assert classify_expiry_status(-1) == EXPIRED

    def test_zero_days_is_expiring_soon(self):
        assert classify_expiry_status(0) == EXPIRING_SOON

    def test_exactly_thirty_days_is_expiring_soon(self):
        assert classify_expiry_status(30) == EXPIRING_SOON

    def test_thirty_one_days_is_safe(self):
        assert classify_expiry_status(31) == SAFE

    def test_none_is_unknown(self):
        assert classify_expiry_status(None) == EXPIRY_UNKNOWN


class TestClassifyStockStatus:
    def test_below_reorder_is_low_stock(self):
        assert classify_stock_status(49, 50, 300) == LOW_STOCK

    def test_zero_stock_is_low_stock(self):
        assert classify_stock_status(0, 50, 300) == LOW_STOCK

    def test_exactly_at_reorder_level_is_normal(self):
        assert classify_stock_status(50, 50, 300) == NORMAL

    def test_exactly_at_maximum_stock_is_normal(self):
        assert classify_stock_status(300, 50, 300) == NORMAL

    def test_above_maximum_is_overstock(self):
        assert classify_stock_status(301, 50, 300) == OVERSTOCK

    def test_within_range_is_normal(self):
        assert classify_stock_status(150, 50, 300) == NORMAL

    def test_negative_stock_is_invalid(self):
        assert classify_stock_status(-1, 50, 300) == STOCK_INVALID

    def test_missing_current_stock_is_invalid(self):
        assert classify_stock_status("", 50, 300) == STOCK_INVALID

    def test_non_numeric_current_stock_is_invalid(self):
        assert classify_stock_status("abc", 50, 300) == STOCK_INVALID

    def test_missing_reorder_level_is_unknown(self):
        assert classify_stock_status(100, "", 300) == STOCK_UNKNOWN

    def test_missing_maximum_stock_is_unknown(self):
        assert classify_stock_status(100, 50, "") == STOCK_UNKNOWN


class TestComputeInventoryValue:
    def test_normal_computation(self):
        assert compute_inventory_value(10, 2.5) == 25.0

    def test_missing_stock_returns_none(self):
        assert compute_inventory_value("", 2.5) is None

    def test_missing_price_returns_none(self):
        assert compute_inventory_value(10, "") is None

    def test_negative_stock_returns_none(self):
        assert compute_inventory_value(-5, 2.5) is None

    def test_rounds_to_two_decimals(self):
        assert compute_inventory_value(3, 1.005) == 3.02 or compute_inventory_value(3, 1.005) == 3.01


class TestIsCriticalRisk:
    def test_critical_and_expired(self):
        assert is_critical_risk(EXPIRED, NORMAL, True) is True

    def test_critical_and_low_stock(self):
        assert is_critical_risk(SAFE, LOW_STOCK, True) is True

    def test_critical_but_only_expiring_soon(self):
        assert is_critical_risk(EXPIRING_SOON, NORMAL, True) is False

    def test_critical_but_only_overstock(self):
        assert is_critical_risk(SAFE, OVERSTOCK, True) is False

    def test_not_critical_medicine_expired(self):
        assert is_critical_risk(EXPIRED, NORMAL, False) is False

    def test_critical_medicine_flag_none(self):
        assert is_critical_risk(EXPIRED, LOW_STOCK, None) is False


class TestComputeRiskScore:
    def test_safe_normal_non_critical(self):
        assert compute_risk_score(SAFE, NORMAL, False) == 0

    def test_expired_alone(self):
        assert compute_risk_score(EXPIRED, NORMAL, False) == 50

    def test_expiring_soon_alone(self):
        assert compute_risk_score(EXPIRING_SOON, NORMAL, False) == 30

    def test_low_stock_alone(self):
        assert compute_risk_score(SAFE, LOW_STOCK, False) == 30

    def test_overstock_alone(self):
        assert compute_risk_score(SAFE, OVERSTOCK, False) == 15

    def test_expired_and_critical(self):
        assert compute_risk_score(EXPIRED, NORMAL, True) == 80

    def test_low_stock_and_critical(self):
        assert compute_risk_score(SAFE, LOW_STOCK, True) == 60

    def test_expiring_soon_and_critical_gets_no_bonus(self):
        assert compute_risk_score(EXPIRING_SOON, NORMAL, True) == 30

    def test_unknown_expiry_contributes_twenty(self):
        assert compute_risk_score(EXPIRY_UNKNOWN, NORMAL, False) == 20

    def test_score_is_capped_at_hundred(self):
        assert compute_risk_score(EXPIRED, LOW_STOCK, True) == 100


class TestClassifyRiskLevel:
    def test_below_twenty_is_low(self):
        assert classify_risk_level(0) == RISK_LOW
        assert classify_risk_level(19) == RISK_LOW

    def test_exactly_twenty_is_medium(self):
        assert classify_risk_level(20) == RISK_MEDIUM

    def test_exactly_forty_is_high(self):
        assert classify_risk_level(40) == RISK_HIGH

    def test_thirty_nine_is_medium(self):
        assert classify_risk_level(39) == RISK_MEDIUM

    def test_exactly_sixty_is_critical(self):
        assert classify_risk_level(60) == RISK_CRITICAL

    def test_fifty_nine_is_high(self):
        assert classify_risk_level(59) == RISK_HIGH

    def test_hundred_is_critical(self):
        assert classify_risk_level(100) == RISK_CRITICAL


class TestRecommendAction:
    def test_no_issues(self):
        action = recommend_action(SAFE, NORMAL, False)
        assert "No action needed" in action

    def test_expired_action(self):
        action = recommend_action(EXPIRED, NORMAL, False)
        assert "Remove from inventory" in action

    def test_low_stock_action(self):
        action = recommend_action(SAFE, LOW_STOCK, False)
        assert "Reorder stock" in action

    def test_overstock_action(self):
        action = recommend_action(SAFE, OVERSTOCK, False)
        assert "Reduce future orders" in action

    def test_critical_risk_prefixed_urgent(self):
        action = recommend_action(EXPIRED, NORMAL, True)
        assert action.startswith("URGENT")

    def test_data_issue_actions(self):
        assert "Verify batch data" in recommend_action(EXPIRY_UNKNOWN, NORMAL, False)
        assert "Verify batch data" in recommend_action(SAFE, STOCK_INVALID, False)
        assert "Verify batch data" in recommend_action(SAFE, STOCK_UNKNOWN, False)


def make_df_row(**overrides) -> dict:
    row = {
        "Batch_ID": "BATCH-0001",
        "Medicine_Name": "Paracetamol 500mg",
        "Category": "Analgesic",
        "Manufacturer": "MediCore Pharma",
        "Manufacturing_Date": "2024-01-01",
        "Expiry_Date": "2026-01-11",
        "Current_Stock": 100,
        "Reorder_Level": 50,
        "Maximum_Stock": 300,
        "Unit_Price": 5.0,
        "Warehouse": "WH-North",
        "Critical_Medicine": "No",
    }
    row.update(overrides)
    return row


class TestApplyRiskEngine:
    def test_adds_all_expected_columns(self):
        df = pd.DataFrame([make_df_row()])
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        for col in [
            "Days_To_Expiry",
            "Expiry_Status",
            "Stock_Status",
            "Inventory_Value",
            "Risk_Score",
            "Risk_Level",
            "Recommended_Action",
        ]:
            assert col in result.columns

    def test_does_not_mutate_input(self):
        df = pd.DataFrame([make_df_row()])
        original_columns = list(df.columns)
        apply_risk_engine(df, reference_date=REFERENCE_DATE)
        assert list(df.columns) == original_columns

    def test_normal_row_is_low_risk(self):
        df = pd.DataFrame([make_df_row(Expiry_Date="2026-06-01")])
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        row = result.iloc[0]
        assert row["Days_To_Expiry"] == 151
        assert row["Expiry_Status"] == SAFE
        assert row["Stock_Status"] == NORMAL
        assert row["Inventory_Value"] == 500.0
        assert row["Risk_Level"] == RISK_LOW

    def test_expired_critical_row_is_critical_risk(self):
        df = pd.DataFrame(
            [make_df_row(Expiry_Date="2025-01-01", Critical_Medicine="Yes")]
        )
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        row = result.iloc[0]
        assert row["Expiry_Status"] == EXPIRED
        assert row["Risk_Level"] == RISK_CRITICAL
        assert row["Recommended_Action"].startswith("URGENT")

    def test_missing_and_invalid_data_handled_without_crashing(self):
        df = pd.DataFrame(
            [
                make_df_row(
                    Expiry_Date="not-a-date",
                    Current_Stock=-5,
                    Unit_Price="",
                    Critical_Medicine="",
                )
            ]
        )
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        row = result.iloc[0]
        assert row["Expiry_Status"] == EXPIRY_UNKNOWN
        assert row["Stock_Status"] == STOCK_INVALID
        assert pd.isna(row["Inventory_Value"])
        assert row["Risk_Level"] in {RISK_LOW, RISK_MEDIUM, RISK_HIGH, RISK_CRITICAL}

    def test_missing_expiry_date_is_unknown(self):
        df = pd.DataFrame([make_df_row(Expiry_Date="")])
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        row = result.iloc[0]
        assert pd.isna(row["Days_To_Expiry"])
        assert row["Expiry_Status"] == EXPIRY_UNKNOWN

    def test_multi_row_dataframe(self):
        df = pd.DataFrame(
            [
                make_df_row(Batch_ID="BATCH-0001"),
                make_df_row(Batch_ID="BATCH-0002", Current_Stock=10),
                make_df_row(Batch_ID="BATCH-0003", Expiry_Date="2025-01-01"),
            ]
        )
        result = apply_risk_engine(df, reference_date=REFERENCE_DATE)
        assert len(result) == 3
        assert result.loc[1, "Stock_Status"] == LOW_STOCK
        assert result.loc[2, "Expiry_Status"] == EXPIRED
