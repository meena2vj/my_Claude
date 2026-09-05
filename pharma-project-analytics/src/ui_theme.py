"""Shared visual constants for the Streamlit dashboard.

Centralised so the same colour maps to the same meaning everywhere -
KPI cards, tables, and Plotly charts alike (per
`.claude/skills/professional-ui/SKILL.md`, "Colour Consistency"). No
Streamlit or Plotly imports here - this module is plain constants only.
"""

from __future__ import annotations

BACKGROUND = "#F7F9FC"
SURFACE = "#FFFFFF"
BORDER = "#E2E8F0"
TEXT_PRIMARY = "#0B2545"
TEXT_MUTED = "#5A6B85"
ACCENT = "#1F5FBF"

MARQUEE_BACKGROUND = "#D6E9FA"
MARQUEE_TEXT = "#0B2545"

RISK_COLORS: dict[str, str] = {
    "Critical": "#D64545",
    "High": "#E08A2A",
    "Medium": "#D6A31C",
    "Low": "#2E9E5B",
}

EXPIRY_COLORS: dict[str, str] = {
    "EXPIRED": "#D64545",
    "EXPIRING_SOON": "#E08A2A",
    "SAFE": "#2E9E5B",
    "UNKNOWN": "#8A93A6",
}

STOCK_COLORS: dict[str, str] = {
    "LOW_STOCK": "#E08A2A",
    "OVERSTOCK": "#6B4FBB",
    "NORMAL": "#2E9E5B",
    "INVALID": "#D64545",
    "UNKNOWN": "#8A93A6",
}

CHART_FONT_FAMILY = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
