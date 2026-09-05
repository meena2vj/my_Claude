"""Deterministic summary reporting over risk-engine output.

Produces plain-data (dict) and markdown-text summaries for human review.
No LLM is used to generate or word any part of the report - every number
comes directly from `risk_engine`/`analytics` and every sentence is a
fixed template. Per docs/GOVERNANCE.md, Critical-risk items are surfaced
for human review only; nothing here takes automated action on them.
"""

from __future__ import annotations

import pandas as pd

from . import analytics
from .data_quality import DataQualityReport


def generate_summary_report(
    df: pd.DataFrame, quality_report: DataQualityReport | None = None
) -> dict:
    """Build a plain-data summary dict combining risk-level counts,
    inventory value at risk, and (optionally) a data-quality summary.
    """
    critical_items = df[df["Risk_Level"] == "Critical"]

    report = {
        "total_batches": len(df),
        "risk_level_counts": analytics.risk_level_counts(df).to_dict(),
        "total_inventory_value_at_risk": analytics.total_inventory_value_at_risk(df),
        "expiring_soon_count": len(analytics.expiring_soon_items(df)),
        "low_stock_count": len(analytics.low_stock_items(df)),
        "overstock_count": len(analytics.overstock_items(df)),
        "critical_risk_batch_ids": critical_items["Batch_ID"].tolist(),
    }

    if quality_report is not None:
        report["data_quality"] = quality_report.summary()

    return report


def generate_markdown_report(
    df: pd.DataFrame, quality_report: DataQualityReport | None = None
) -> str:
    """Render `generate_summary_report` as a human-readable markdown string."""
    summary = generate_summary_report(df, quality_report)

    lines = ["# Pharma Inventory Risk Summary", ""]
    lines.append(f"Total batches analysed: **{summary['total_batches']}**")
    lines.append("")

    lines.append("## Risk Levels")
    for level in ["Critical", "High", "Medium", "Low"]:
        count = summary["risk_level_counts"].get(level, 0)
        lines.append(f"- {level}: {count}")
    lines.append("")

    lines.append("## Key Figures")
    lines.append(
        f"- Inventory value at risk (Critical + High): "
        f"{summary['total_inventory_value_at_risk']:.2f}"
    )
    lines.append(f"- Expiring soon or expired batches: {summary['expiring_soon_count']}")
    lines.append(f"- Low stock batches: {summary['low_stock_count']}")
    lines.append(f"- Overstock batches: {summary['overstock_count']}")
    lines.append("")

    lines.append("## Critical Risk - Requires Human Review")
    if summary["critical_risk_batch_ids"]:
        for batch_id in summary["critical_risk_batch_ids"]:
            lines.append(f"- {batch_id}")
    else:
        lines.append("- None")
    lines.append("")

    if "data_quality" in summary:
        dq = summary["data_quality"]
        lines.append("## Data Quality")
        lines.append(f"- Rows with missing values: {dq['missing_value_counts']}")
        lines.append(
            f"- Duplicate rows: {dq['duplicate_row_count']} "
            f"in {dq['duplicate_group_count']} group(s)"
        )
        lines.append(
            f"- Duplicate Batch_IDs: {dq['duplicate_batch_id_row_count']} "
            f"in {dq['duplicate_batch_id_group_count']} group(s)"
        )
        lines.append(f"- Rows with invalid dates: {dq['invalid_date_row_count']}")
        lines.append(f"- Rows with negative stock: {dq['negative_stock_row_count']}")
        lines.append("")

    return "\n".join(lines)
