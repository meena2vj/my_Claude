"""Pharma Project Analytics - Streamlit entry point.

Wiring only, per CLAUDE.md ("app.py (entry point/wiring only)"): this
module loads/validates data, applies the risk engine and data-quality
checks, and dispatches to the UI render functions in `src/ui/`. No
classification or filtering logic lives here - see `src/risk_engine.py`,
`src/data_quality.py`, and `src/filters.py`.

No LLM, database, or authentication is used anywhere in this app.
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from src import data_loader, data_quality, risk_engine, upload
from src.data_loader import DataValidationError
from src.filters import apply_filters
from src.ui import header, sidebar, states, tabs

SAMPLE_DATA_PATH = Path(__file__).parent / "data" / "pharma_inventory.csv"


def _max_upload_size_mb() -> float:
    """Optional override via the MAX_UPLOAD_SIZE_MB env var (see
    .env.example); falls back to upload.py's documented default.
    """
    raw = os.getenv("MAX_UPLOAD_SIZE_MB")
    if not raw:
        return upload.DEFAULT_MAX_SIZE_MB
    try:
        return float(raw)
    except ValueError:
        return upload.DEFAULT_MAX_SIZE_MB


# TTL bounds how long a processed dataset stays in Streamlit's
# process-wide cache, so an upload never lingers far past "this session"
# (docs/GOVERNANCE.md "Session-Only Processing") even though cache_data
# itself is shared across concurrent users of one server process.
_CACHE_TTL_SECONDS = 3600


@st.cache_data(show_spinner=False, ttl=_CACHE_TTL_SECONDS)
def _load_and_enrich_sample():
    raw = data_loader.load_inventory_csv(SAMPLE_DATA_PATH)
    enriched = risk_engine.apply_risk_engine(raw)
    quality_report = data_quality.run_data_quality_checks(raw)
    return enriched, quality_report


@st.cache_data(show_spinner=False, ttl=_CACHE_TTL_SECONDS)
def _load_and_enrich_upload(file_bytes: bytes, filename: str, max_size_mb: float):
    buffer = io.BytesIO(file_bytes)
    buffer.name = filename
    buffer.size = len(file_bytes)
    raw = upload.load_inventory_upload(buffer, max_size_mb=max_size_mb)
    enriched = risk_engine.apply_risk_engine(raw)
    quality_report = data_quality.run_data_quality_checks(raw)
    return enriched, quality_report


def main() -> None:
    st.set_page_config(page_title="Pharma Project Analytics", layout="wide")
    header.render_header()

    uploaded_file = sidebar.render_uploader()

    df = None
    quality_report = None
    active_upload_ok = False

    try:
        with st.spinner(states.LOADING_MESSAGE):
            if uploaded_file is not None:
                df, quality_report = _load_and_enrich_upload(
                    uploaded_file.getvalue(), uploaded_file.name, _max_upload_size_mb()
                )
                active_upload_ok = True
            else:
                df, quality_report = _load_and_enrich_sample()
    except DataValidationError as exc:
        states.render_invalid_file_state(str(exc))
        try:
            with st.spinner(states.LOADING_MESSAGE):
                df, quality_report = _load_and_enrich_sample()
        except Exception:
            st.stop()
    except Exception:
        states.render_unexpected_error_state()
        st.stop()

    processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if active_upload_ok:
        states.render_success_state(uploaded_file.name, len(df), processed_at)
    else:
        st.caption(f"Using bundled sample dataset — {len(df):,} row(s) — processed {processed_at}.")

    selection = sidebar.render_filters(df)
    filtered_df = apply_filters(df, selection)

    tab_names = [
        "Executive Dashboard",
        "Risk Analysis",
        "Data Quality",
        "Data Preview",
        "Governance",
    ]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)

    with tab1:
        tabs.render_executive_dashboard_tab(filtered_df)
    with tab2:
        tabs.render_risk_analysis_tab(filtered_df)
    with tab3:
        tabs.render_data_quality_tab(df, quality_report)
    with tab4:
        tabs.render_data_preview_tab(filtered_df)
    with tab5:
        tabs.render_governance_tab(quality_report)


if __name__ == "__main__":
    main()
