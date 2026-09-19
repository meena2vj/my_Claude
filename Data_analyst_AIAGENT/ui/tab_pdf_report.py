"""Tab: downloadable PDF report."""

from pathlib import Path

import streamlit as st

from agents import report_agent
from graph.node_runner import run_node
from graph.state import AgentState
from ui import theme


def render(state: AgentState) -> None:
    st.subheader("PDF Report")
    if state["insights"] is None:
        st.info("Generate insights first.")
        return

    if st.button("Generate PDF report", type="primary"):
        state.update(run_node("report", report_agent.run, state))
        st.rerun()

    theme.render_last_error(state)

    if not state["report_path"]:
        st.caption("No report generated yet.")
        return

    path = Path(state["report_path"])
    if path.exists():
        st.success(f"Report ready: {path.name}")
        st.download_button(
            "Download PDF report",
            data=path.read_bytes(),
            file_name=path.name,
            mime="application/pdf",
        )
