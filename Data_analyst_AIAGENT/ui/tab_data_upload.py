"""Tab: upload a CSV/XLSX, validate it, and preview rows/columns/dtypes."""

import pandas as pd
import streamlit as st

from graph.state import AgentState
from tools.file_validation import FileValidationError, load_dataframe, validate_and_save


def render(state: AgentState) -> None:
    st.subheader("Data Upload")
    if not (state["problem_statement"].strip() and state["kpis"]):
        st.info("Complete the Business Context tab first.")
        return

    uploaded_file = st.file_uploader("Upload a dataset", type=["csv", "xlsx"])

    if uploaded_file is not None and st.button("Validate & load", type="primary"):
        try:
            validated = validate_and_save(uploaded_file)
            df, meta = load_dataframe(validated)
        except FileValidationError as exc:
            st.error(str(exc))
        else:
            state["raw_data"] = df
            state["raw_data_meta"] = meta
            state["quality_report"] = None
            state["cleaning_plan"] = []
            state["cleaning_log"] = []
            state["clean_data"] = None
            state["cleaning_confirmed"] = False
            state["status"] = "in_progress"
            st.success(f"Loaded '{meta.filename}' -- {meta.rows} rows x {meta.columns} columns.")

    if state["raw_data"] is not None:
        meta = state["raw_data_meta"]
        st.markdown("#### Preview")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows", meta.rows)
        c2.metric("Columns", meta.columns)
        c3.metric("File", meta.filename)
        st.dataframe(state["raw_data"].head(20), use_container_width=True)
        st.markdown("#### Column data types")
        st.dataframe(
            pd.DataFrame({"column": meta.dtypes.keys(), "dtype": meta.dtypes.values()}),
            use_container_width=True,
            hide_index=True,
        )
        st.caption("Continue to Data Quality once you're happy with the preview.")
