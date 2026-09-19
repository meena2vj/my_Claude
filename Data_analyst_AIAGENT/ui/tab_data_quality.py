"""Tab: Data Quality Report -- issue counts and percentages, pure Pandas/NumPy."""

import pandas as pd
import streamlit as st

from graph.node_runner import run_node
from graph.state import AgentState
from tools.data_profiling import profile_dataframe
from ui import theme


def _issues_table(issues) -> pd.DataFrame:
    return pd.DataFrame([{"column": i.column, "count": i.count, "percentage": i.percentage} for i in issues])


def render(state: AgentState) -> None:
    st.subheader("Data Quality")
    if state["raw_data"] is None:
        st.info("Upload a dataset first.")
        return

    if state["quality_report"] is None:
        if st.button("Run data quality analysis", type="primary"):
            state.update(
                run_node(
                    "quality",
                    lambda s: {"quality_report": profile_dataframe(s["raw_data"])},
                    state,
                )
            )
            st.rerun()
        theme.render_last_error(state)
        return

    report = state["quality_report"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", report.row_count)
    c2.metric("Columns", report.column_count)
    c3.metric("Duplicate rows", f"{report.duplicate_row_count} ({report.duplicate_row_percentage}%)")

    st.markdown("#### Missing values")
    if report.missing_by_column:
        st.dataframe(_issues_table(report.missing_by_column), use_container_width=True, hide_index=True)
    else:
        st.caption("No missing values detected.")

    st.markdown("#### Outliers (IQR method)")
    if report.outliers_by_column:
        st.dataframe(_issues_table(report.outliers_by_column), use_container_width=True, hide_index=True)
    else:
        st.caption("No outliers detected.")

    st.markdown("#### Invalid / blank values")
    if report.invalid_value_columns:
        st.dataframe(_issues_table(report.invalid_value_columns), use_container_width=True, hide_index=True)
    else:
        st.caption("No invalid or blank values detected.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### Numeric columns")
        st.write(report.numeric_columns or "None")
        st.markdown("#### Constant columns")
        st.write(report.constant_columns or "None")
    with col_b:
        st.markdown("#### Categorical columns")
        st.write(report.categorical_columns or "None")
        st.markdown("#### Unique value counts")
        st.dataframe(
            pd.DataFrame({"column": report.unique_counts.keys(), "unique_values": report.unique_counts.values()}),
            use_container_width=True,
            hide_index=True,
        )

    if report.descriptive_stats:
        st.markdown("#### Descriptive statistics")
        st.dataframe(pd.DataFrame(report.descriptive_stats).T, use_container_width=True)

    st.caption("Continue to Data Cleaning to review and confirm the cleaning plan.")
