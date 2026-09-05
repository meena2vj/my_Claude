"""Plotly figure builders for the five required charts.

Each function takes the (already filtered) risk-engine-enriched
DataFrame and returns a `plotly.graph_objects.Figure`. Pure data-to-figure
functions - no Streamlit calls here, so they stay easy to reason about
and reuse the same colour maps as the KPI cards (`src/ui_theme.py`).
Every chart has axis labels, a legend where more than one series appears,
and plain-language hover text, per
`.claude/skills/professional-ui/SKILL.md` ("Accessible Charts").
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .. import analytics, ui_theme

RISK_LEVEL_ORDER = ["Critical", "High", "Medium", "Low"]
EXPIRY_STATUS_ORDER = ["EXPIRED", "EXPIRING_SOON", "SAFE", "UNKNOWN"]

_LAYOUT_DEFAULTS = dict(
    font=dict(family=ui_theme.CHART_FONT_FAMILY, color=ui_theme.TEXT_PRIMARY),
    plot_bgcolor=ui_theme.SURFACE,
    paper_bgcolor=ui_theme.SURFACE,
    margin=dict(l=40, r=20, t=50, b=40),
)


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        showarrow=False,
        font=dict(size=14, color=ui_theme.TEXT_MUTED),
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        **_LAYOUT_DEFAULTS,
    )
    return fig


def build_risk_level_chart(df: pd.DataFrame) -> go.Figure:
    """Batches by Risk Level."""
    if df.empty:
        return _empty_figure("No batches match the current filters.")

    counts = analytics.risk_level_counts(df).reindex(RISK_LEVEL_ORDER).fillna(0).astype(int)
    fig = px.bar(
        x=counts.index,
        y=counts.values,
        color=counts.index,
        color_discrete_map=ui_theme.RISK_COLORS,
        labels={"x": "Risk Level", "y": "Number of Batches", "color": "Risk Level"},
        title="Batches by Risk Level",
    )
    fig.update_traces(hovertemplate="Risk Level: %{x}<br>Batches: %{y}<extra></extra>")
    fig.update_layout(showlegend=True, **_LAYOUT_DEFAULTS)
    return fig


def build_inventory_value_by_category_chart(df: pd.DataFrame) -> go.Figure:
    """Inventory Value by Category."""
    if df.empty:
        return _empty_figure("No batches match the current filters.")

    values = analytics.inventory_value_by_category(df).sort_values(ascending=False)
    if values.empty:
        return _empty_figure("No batches with a valid inventory value.")

    fig = px.bar(
        x=values.index,
        y=values.values,
        labels={"x": "Category", "y": "Inventory Value"},
        title="Inventory Value by Category",
    )
    fig.update_traces(
        marker_color=ui_theme.ACCENT,
        hovertemplate="Category: %{x}<br>Inventory Value: %{y:,.2f}<extra></extra>",
    )
    fig.update_layout(showlegend=False, **_LAYOUT_DEFAULTS)
    return fig


def build_expiry_timeline_chart(df: pd.DataFrame) -> go.Figure:
    """Expiry Timeline - distribution of days to expiry, coloured by status."""
    if df.empty:
        return _empty_figure("No batches match the current filters.")

    plot_df = df.dropna(subset=["Days_To_Expiry"]).copy()
    if plot_df.empty:
        return _empty_figure("No batches with a known expiry date.")

    fig = px.histogram(
        plot_df,
        x="Days_To_Expiry",
        color="Expiry_Status",
        category_orders={"Expiry_Status": EXPIRY_STATUS_ORDER},
        color_discrete_map=ui_theme.EXPIRY_COLORS,
        labels={"Days_To_Expiry": "Days to Expiry", "count": "Number of Batches",
                "Expiry_Status": "Expiry Status"},
        title="Expiry Timeline",
    )
    fig.update_traces(
        hovertemplate="Days to Expiry: %{x}<br>Batches: %{y}<extra></extra>"
    )
    fig.update_layout(showlegend=True, bargap=0.1, **_LAYOUT_DEFAULTS)
    return fig


def build_low_stock_by_warehouse_chart(df: pd.DataFrame) -> go.Figure:
    """Low Stock by Warehouse."""
    if df.empty:
        return _empty_figure("No batches match the current filters.")

    low_stock = analytics.low_stock_items(df)
    if low_stock.empty:
        return _empty_figure("No low-stock batches in the current selection.")

    counts = low_stock.groupby("Warehouse").size().sort_values(ascending=False)
    fig = px.bar(
        x=counts.index,
        y=counts.values,
        labels={"x": "Warehouse", "y": "Low-Stock Batches"},
        title="Low Stock by Warehouse",
    )
    fig.update_traces(
        marker_color=ui_theme.STOCK_COLORS["LOW_STOCK"],
        hovertemplate="Warehouse: %{x}<br>Low-Stock Batches: %{y}<extra></extra>",
    )
    fig.update_layout(showlegend=False, **_LAYOUT_DEFAULTS)
    return fig


def build_top_critical_batches_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Top Critical Medicine Batches - highest Risk_Score among batches
    flagged Critical_Medicine = Yes.
    """
    if df.empty:
        return _empty_figure("No batches match the current filters.")

    critical_medicine = df[
        df["Critical_Medicine"].astype(str).str.strip().str.lower() == "yes"
    ]
    if critical_medicine.empty:
        return _empty_figure("No critical-medicine batches in the current selection.")

    top = critical_medicine.sort_values("Risk_Score", ascending=False).head(top_n)
    top = top.iloc[::-1]  # highest risk at the top of a horizontal bar chart

    fig = px.bar(
        top,
        x="Risk_Score",
        y="Medicine_Name",
        color="Risk_Level",
        orientation="h",
        color_discrete_map=ui_theme.RISK_COLORS,
        category_orders={"Risk_Level": RISK_LEVEL_ORDER},
        labels={"Risk_Score": "Risk Score", "Medicine_Name": "Medicine", "Risk_Level": "Risk Level"},
        title="Top Critical Medicine Batches",
        hover_data={"Batch_ID": True, "Warehouse": True},
    )
    fig.update_layout(showlegend=True, **_LAYOUT_DEFAULTS)
    return fig
