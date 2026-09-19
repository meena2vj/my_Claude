"""Tab: facts, trends, anomalies, RAG-grounded recommendations."""

import streamlit as st

from agents import insight_agent
from graph.node_runner import run_node
from graph.state import AgentState, InsightItem
from ui import theme


def _tag_label(item: InsightItem) -> str:
    if item.tag == "cited" and item.citation:
        return f"source: {item.citation.filename} p.{item.citation.page}"
    return "data-derived"


def render(state: AgentState) -> None:
    st.subheader("Insights")
    if state["analysis_result"] is None:
        st.info("Ask a question in Ask Your Data first.")
        return

    if st.button("Generate insights", type="primary"):
        state.update(run_node("insight", insight_agent.run, state))
        st.rerun()

    theme.render_last_error(state)

    insights = state["insights"]
    if insights is None:
        st.caption("Click 'Generate insights' to analyze facts, trends, and recommendations.")
        return

    st.markdown("#### Key Facts")
    for item in insights.facts:
        st.markdown(f"- {item.text}  \n  *({_tag_label(item)})*")

    if insights.trends:
        st.markdown("#### Trends")
        for t in insights.trends:
            st.markdown(f"- {t}")

    if insights.anomalies:
        st.markdown("#### Anomalies")
        for a in insights.anomalies:
            st.markdown(f"- {a}")

    st.markdown("#### Recommendations")
    if insights.recommendations:
        for item in insights.recommendations:
            st.markdown(f"- {item.text}  \n  *({_tag_label(item)})*")
    else:
        st.caption("No recommendations generated.")
