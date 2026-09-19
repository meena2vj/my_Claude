"""Tab: Plotly dashboard grounded in analysis results."""

import json

import plotly.graph_objects as go
import streamlit as st

from graph.state import AgentState


def render(state: AgentState) -> None:
    st.subheader("Dashboard")
    if not state["charts"]:
        st.info("Ask a question in Ask Your Data to generate charts.")
        return

    for chart in reversed(state["charts"]):
        st.markdown(f"**{chart.question}**")
        fig = go.Figure(json.loads(chart.plotly_json))
        st.plotly_chart(fig, use_container_width=True)
        st.divider()
