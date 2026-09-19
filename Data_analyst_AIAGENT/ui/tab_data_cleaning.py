"""Tab: cleaning plan proposal, user confirmation, and before/after view."""

import pandas as pd
import streamlit as st

from graph.node_runner import run_node
from graph.state import AgentState
from tools.data_cleaning_ops import build_default_plan, execute_plan
from ui import theme


def render(state: AgentState) -> None:
    st.subheader("Data Cleaning")
    if state["quality_report"] is None:
        st.info("Run the Data Quality step first.")
        return

    if not state["cleaning_plan"]:
        if st.button("Generate cleaning plan", type="primary"):
            state.update(
                run_node(
                    "cleaning",
                    lambda s: {"cleaning_plan": build_default_plan(s["raw_data"], s["quality_report"])},
                    state,
                )
            )
            if not state["cleaning_plan"]:
                state["clean_data"] = state["raw_data"].copy(deep=True)
                state["cleaning_confirmed"] = True
            st.rerun()
        theme.render_last_error(state)
        return

    if state["clean_data"] is None:
        st.markdown("#### Proposed cleaning plan")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "action": a.action_type,
                        "column": a.column or "-",
                        "description": a.description,
                        "destructive": a.destructive,
                    }
                    for a in state["cleaning_plan"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        if any(a.destructive for a in state["cleaning_plan"]):
            st.warning("This plan includes destructive actions (e.g. dropping duplicate rows).")
        confirmed = st.checkbox("I've reviewed this plan and confirm it should be applied.")
        if st.button("Confirm & run cleaning", type="primary", disabled=not confirmed):
            state["cleaning_confirmed"] = True

            def _execute(s: AgentState) -> dict:
                clean_df, log = execute_plan(s["raw_data"], s["cleaning_plan"])
                return {"clean_data": clean_df, "cleaning_log": log}

            state.update(run_node("cleaning", _execute, state))
            st.rerun()
        theme.render_last_error(state)
        return

    st.success("Cleaning applied.")
    st.markdown("#### Before -> After")
    c1, c2 = st.columns(2)
    c1.metric("Rows before", len(state["raw_data"]))
    c2.metric("Rows after", len(state["clean_data"]))

    st.markdown("#### Cleaning audit trail")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "action": a.action_type,
                    "column": a.column or "-",
                    "description": a.description,
                    "rows_before": a.rows_before,
                    "rows_after": a.rows_after,
                }
                for a in state["cleaning_log"]
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Clean dataset preview")
    st.dataframe(state["clean_data"].head(20), use_container_width=True)
    st.download_button(
        "Download clean dataset (CSV)",
        data=state["clean_data"].to_csv(index=False).encode("utf-8"),
        file_name="clean_data.csv",
        mime="text/csv",
    )
    st.caption("Continue to Ask Your Data.")
