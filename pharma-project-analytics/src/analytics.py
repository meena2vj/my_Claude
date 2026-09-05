"""Aggregate analytics over a risk-engine-enriched inventory DataFrame.

Every function here expects a DataFrame that already has the columns
added by `risk_engine.apply_risk_engine` (Risk_Level, Stock_Status,
Expiry_Status, Inventory_Value, ...). These are plain deterministic
pandas aggregations - no ML, no LLM.
"""

from __future__ import annotations

import pandas as pd

from .risk_engine import EXPIRED, EXPIRING_SOON, LOW_STOCK, OVERSTOCK


def risk_level_counts(df: pd.DataFrame) -> pd.Series:
    """Count of batches per Risk_Level."""
    return df["Risk_Level"].value_counts()


def inventory_value_by_category(df: pd.DataFrame) -> pd.Series:
    """Total Inventory_Value per medicine Category (rows with an
    unknown/invalid Inventory_Value are excluded from the sum).
    """
    return df.dropna(subset=["Inventory_Value"]).groupby("Category")["Inventory_Value"].sum()


def total_inventory_value_at_risk(
    df: pd.DataFrame, risk_levels: tuple[str, ...] = ("Critical", "High")
) -> float:
    """Sum of Inventory_Value for batches whose Risk_Level is in `risk_levels`."""
    subset = df[df["Risk_Level"].isin(risk_levels)]
    return float(subset["Inventory_Value"].dropna().sum())


def expiring_soon_items(df: pd.DataFrame) -> pd.DataFrame:
    """Batches classified EXPIRED or EXPIRING_SOON, ordered soonest first."""
    subset = df[df["Expiry_Status"].isin([EXPIRED, EXPIRING_SOON])]
    return subset.sort_values("Days_To_Expiry", na_position="last")


def low_stock_items(df: pd.DataFrame) -> pd.DataFrame:
    """Batches classified LOW_STOCK, ordered by lowest Current_Stock first."""
    subset = df[df["Stock_Status"] == LOW_STOCK]
    return subset.sort_values("Current_Stock")


def overstock_items(df: pd.DataFrame) -> pd.DataFrame:
    """Batches classified OVERSTOCK, ordered by highest Current_Stock first."""
    subset = df[df["Stock_Status"] == OVERSTOCK]
    return subset.sort_values("Current_Stock", ascending=False)


def critical_medicine_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Risk_Level counts restricted to rows flagged Critical_Medicine = Yes."""
    critical = df[df["Critical_Medicine"].astype(str).str.strip().str.lower() == "yes"]
    return critical.groupby("Risk_Level").size().rename("Batch_Count").reset_index()


def warehouse_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-warehouse batch count and total Inventory_Value."""
    return df.groupby("Warehouse").agg(
        Batch_Count=("Batch_ID", "count"),
        Total_Inventory_Value=("Inventory_Value", "sum"),
    )
