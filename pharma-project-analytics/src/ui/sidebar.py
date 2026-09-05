"""Sidebar: file uploader, filter widgets, and the Reset Filters button.

Split into two render calls because the filter *options* depend on the
dataset that results from the uploader's own value - `render_uploader()`
must run and be resolved by the caller before `render_filters(df)` can
know what options to offer. Rendering only: all filtering logic lives in
`src/filters.py` and all upload validation/parsing lives in
`src/upload.py` (per CLAUDE.md, "No business logic inside Streamlit
callback/render functions").
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import streamlit as st

from ..data_loader import REQUIRED_COLUMNS
from ..filters import FilterSelection
from ..upload import ALLOWED_UPLOAD_EXTENSIONS
from .states import UPLOAD_HELP_MESSAGE

FILTER_KEYS = [
    "medicine_filter",
    "category_filter",
    "warehouse_filter",
    "expiry_filter",
    "stock_filter",
    "risk_filter",
]


def _sorted_unique(df: pd.DataFrame, column: str) -> list[str]:
    if column not in df.columns:
        return []
    return sorted(v for v in df[column].dropna().unique().tolist() if str(v).strip())


def render_uploader() -> Optional[Any]:
    """Render the CSV/Excel uploader. Returns the uploaded file object, or
    None if nothing is currently uploaded.
    """
    with st.sidebar:
        st.markdown("### Upload Inventory Data")
        uploaded_file = st.file_uploader(
            "CSV or Excel file",
            type=sorted(ext.lstrip(".") for ext in ALLOWED_UPLOAD_EXTENSIONS),
            help=f"Expected columns: {', '.join(REQUIRED_COLUMNS)}",
        )
        st.caption(UPLOAD_HELP_MESSAGE)
    return uploaded_file


def render_filters(df: pd.DataFrame) -> FilterSelection:
    """Render the filter widgets and Reset Filters button. Returns the
    current FilterSelection built from widget state.
    """
    with st.sidebar:
        st.markdown("---")
        st.markdown("### Filters")

        medicines = st.multiselect(
            "Medicine", _sorted_unique(df, "Medicine_Name"), key="medicine_filter"
        )
        categories = st.multiselect(
            "Category", _sorted_unique(df, "Category"), key="category_filter"
        )
        warehouses = st.multiselect(
            "Warehouse", _sorted_unique(df, "Warehouse"), key="warehouse_filter"
        )
        expiry_statuses = st.multiselect(
            "Expiry Status", _sorted_unique(df, "Expiry_Status"), key="expiry_filter"
        )
        stock_statuses = st.multiselect(
            "Stock Status", _sorted_unique(df, "Stock_Status"), key="stock_filter"
        )
        risk_levels = st.multiselect(
            "Risk Level", _sorted_unique(df, "Risk_Level"), key="risk_filter"
        )

        if st.button("Reset Filters", use_container_width=True):
            for key in FILTER_KEYS:
                st.session_state.pop(key, None)
            st.rerun()

    return FilterSelection(
        medicines=medicines,
        categories=categories,
        warehouses=warehouses,
        expiry_statuses=expiry_statuses,
        stock_statuses=stock_statuses,
        risk_levels=risk_levels,
    )
