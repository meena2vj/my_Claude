"""KPI card row: Total Batches, Total Inventory Value, Expired Batches,
Expiring Soon, Low-Stock Batches, Critical-Risk Batches.

Card values are computed here from an already risk-engine-enriched
DataFrame using plain pandas - no new business rules are invented (the
underlying classifications all come from `src/risk_engine.py`).
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import ui_theme
from ..risk_engine import EXPIRED, EXPIRING_SOON, LOW_STOCK, RISK_CRITICAL


def _card_html(label: str, value: str, accent: str) -> str:
    return f"""
    <div style="
        background: {ui_theme.SURFACE};
        border: 1px solid {ui_theme.BORDER};
        border-top: 4px solid {accent};
        border-radius: 8px;
        padding: 0.9rem 1rem;
        text-align: left;
        min-height: 5.5rem;
    ">
        <div style="color:{ui_theme.TEXT_MUTED}; font-size:0.8rem; font-weight:600;
                    text-transform:uppercase; letter-spacing:0.03em; margin-bottom:0.25rem;
                    white-space: nowrap;">
            {label}
        </div>
        <div style="color:{ui_theme.TEXT_PRIMARY}; font-size:1.4rem; font-weight:700;
                    white-space: nowrap;">
            {value}
        </div>
    </div>
    """


def _format_currency(value: float) -> str:
    """Compact currency formatting so large totals never wrap inside a
    fixed-width KPI card (e.g. 13,404,646.31 -> 13.40M).
    """
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if abs_value >= 1_000:
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def render_kpi_cards(df: pd.DataFrame) -> None:
    """Render the six KPI cards in one responsive row."""
    total_batches = len(df)
    total_value = df["Inventory_Value"].dropna().sum() if "Inventory_Value" in df else 0.0
    expired_count = int((df["Expiry_Status"] == EXPIRED).sum()) if "Expiry_Status" in df else 0
    expiring_soon_count = (
        int((df["Expiry_Status"] == EXPIRING_SOON).sum()) if "Expiry_Status" in df else 0
    )
    low_stock_count = int((df["Stock_Status"] == LOW_STOCK).sum()) if "Stock_Status" in df else 0
    critical_count = int((df["Risk_Level"] == RISK_CRITICAL).sum()) if "Risk_Level" in df else 0

    cards = [
        ("Total Batches", f"{total_batches:,}", ui_theme.ACCENT),
        ("Total Inventory Value", _format_currency(total_value), ui_theme.ACCENT),
        ("Expired Batches", f"{expired_count:,}", ui_theme.RISK_COLORS["Critical"]),
        ("Expiring Soon", f"{expiring_soon_count:,}", ui_theme.RISK_COLORS["High"]),
        ("Low-Stock Batches", f"{low_stock_count:,}", ui_theme.RISK_COLORS["High"]),
        ("Critical-Risk Batches", f"{critical_count:,}", ui_theme.RISK_COLORS["Critical"]),
    ]

    columns = st.columns(len(cards))
    for column, (label, value, accent) in zip(columns, cards):
        with column:
            st.markdown(_card_html(label, value, accent), unsafe_allow_html=True)
