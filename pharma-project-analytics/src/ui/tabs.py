"""The five dashboard tabs: Executive Dashboard, Risk Analysis, Data
Quality, Data Preview, Governance - including their download buttons.

Rendering only: all numbers come from `src/analytics.py`,
`src/report_generator.py`, and the risk-engine-enriched DataFrame passed
in. No new business logic is defined here.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from .. import analytics, report_generator
from ..data_quality import DataQualityReport
from ..risk_engine import RISK_CRITICAL
from . import charts, kpi, states


def render_executive_dashboard_tab(filtered_df: pd.DataFrame) -> None:
    if filtered_df.empty:
        states.render_empty_data_state("the current filters")
        return

    kpi.render_kpi_cards(filtered_df)
    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(charts.build_risk_level_chart(filtered_df), use_container_width=True)
    with col2:
        st.plotly_chart(
            charts.build_inventory_value_by_category_chart(filtered_df),
            use_container_width=True,
        )

    st.download_button(
        "Download Processed Inventory Report (CSV)",
        data=filtered_df.to_csv(index=False).encode("utf-8"),
        file_name="processed_inventory_report.csv",
        mime="text/csv",
    )


def render_risk_analysis_tab(filtered_df: pd.DataFrame) -> None:
    if filtered_df.empty:
        states.render_empty_data_state("the current filters")
        return

    st.plotly_chart(charts.build_expiry_timeline_chart(filtered_df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            charts.build_low_stock_by_warehouse_chart(filtered_df), use_container_width=True
        )
    with col2:
        st.plotly_chart(
            charts.build_top_critical_batches_chart(filtered_df), use_container_width=True
        )

    critical_items = filtered_df[filtered_df["Risk_Level"] == RISK_CRITICAL]
    st.markdown("#### Critical-Risk Batches — Flagged for Human Review")
    st.caption(
        "Per project governance, Critical-Risk items are surfaced for human "
        "review only; this dashboard never takes automated action on them."
    )
    if critical_items.empty:
        st.info("No Critical-Risk batches in the current selection.")
    else:
        st.dataframe(
            critical_items[
                ["Batch_ID", "Medicine_Name", "Warehouse", "Expiry_Status",
                 "Stock_Status", "Risk_Score", "Recommended_Action"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        "Download Critical-Risk Report (CSV)",
        data=critical_items.to_csv(index=False).encode("utf-8"),
        file_name="critical_risk_report.csv",
        mime="text/csv",
    )


def render_data_quality_tab(full_df: pd.DataFrame, quality_report: DataQualityReport) -> None:
    st.markdown("#### Data-Quality Summary")
    st.caption(
        "Detected only, never silently repaired or dropped - flagged for review."
    )
    summary = quality_report.summary()

    cols = st.columns(4)
    cols[0].metric("Rows Checked", f"{summary['total_rows']:,}")
    cols[1].metric(
        "Rows with Missing Values",
        f"{sum(summary['missing_value_counts'].values()):,}",
    )
    cols[2].metric("Duplicate Rows", f"{summary['duplicate_row_count']:,}")
    cols[3].metric("Negative-Stock Rows", f"{summary['negative_stock_row_count']:,}")

    if summary["missing_value_counts"]:
        st.markdown("**Missing values by column**")
        st.dataframe(
            pd.DataFrame(
                summary["missing_value_counts"].items(), columns=["Column", "Missing Rows"]
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown(
        f"- Duplicate Batch_IDs: **{summary['duplicate_batch_id_row_count']}** row(s) "
        f"in **{summary['duplicate_batch_id_group_count']}** group(s)\n"
        f"- Rows with invalid dates: **{summary['invalid_date_row_count']}**"
    )

    if not quality_report.has_issues():
        st.success("No data-quality issues detected in the current dataset.")

    markdown_report = report_generator.generate_markdown_report(full_df, quality_report)
    st.download_button(
        "Download Data-Quality Report (Markdown)",
        data=markdown_report.encode("utf-8"),
        file_name="data_quality_report.md",
        mime="text/markdown",
    )


def render_data_preview_tab(filtered_df: pd.DataFrame) -> None:
    st.markdown("#### Data Preview")
    st.caption("Read-only preview of the currently filtered dataset, including risk-engine columns.")
    if filtered_df.empty:
        states.render_empty_data_state("the current filters")
        return
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)


def render_governance_tab(quality_report: DataQualityReport) -> None:
    st.markdown("#### Data & Governance Notice")
    st.info(
        "**Synthetic data notice:** All data used in this dashboard is synthetic "
        "or de-identified operational sample data. No production or real-world "
        "sourced data is loaded."
    )
    st.warning(
        "**No medical advice:** This tool performs inventory and expiry analytics "
        "only. It does not diagnose, recommend treatment, calculate dosage, or "
        "provide medical advice of any kind."
    )

    st.markdown("**Calculation rules (see `.claude/skills/pharma-risk/SKILL.md`):**")
    st.markdown(
        "- **Expiry Status:** `EXPIRED` if past due; `EXPIRING_SOON` if due within "
        "30 days; `SAFE` otherwise; `UNKNOWN` if the expiry date is missing/invalid.\n"
        "- **Stock Status:** `LOW_STOCK` if current stock is below the reorder "
        "level; `OVERSTOCK` if above the maximum stock level; `NORMAL` otherwise.\n"
        "- **Critical Risk:** the medicine is flagged critical **and** is either "
        "expired or low on stock. Critical-Risk items are surfaced for human "
        "review only - the dashboard never acts on them automatically.\n"
        "- All classifications are deterministic Python rules. No machine "
        "learning or LLM is used anywhere in this dashboard."
    )

    st.markdown("**Data-quality issues in the current dataset:**")
    summary = quality_report.summary()
    if quality_report.has_issues():
        st.json(summary)
    else:
        st.success("No data-quality issues detected.")

    st.markdown(
        "**Session-only processing:** Uploaded files are read directly into "
        "memory for this session only. Nothing you upload is written to disk "
        "or sent to any external service."
    )
    st.caption(f"Governance notice rendered {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.")
