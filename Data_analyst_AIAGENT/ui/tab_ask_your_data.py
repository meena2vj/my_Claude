"""Tab: chat interface over the cleaned dataset."""

from datetime import datetime, timezone

import streamlit as st

from agents import analyst_agent, visualization_agent
from config.settings import MAX_ANALYST_RETRIES
from graph.node_runner import run_node
from graph.state import AgentError, AgentState
from ui import theme


def render(state: AgentState) -> None:
    st.subheader("Ask Your Data")
    if state["clean_data"] is None:
        st.info("Complete Data Cleaning first.")
        return

    for turn in state["conversation_history"]:
        with st.chat_message(turn.role):
            st.write(turn.content)

    question = st.chat_input("Ask a question about your cleaned data...")
    if question:
        state["user_question"] = question
        state["status"] = "in_progress"
        state.update(run_node("analyst", analyst_agent.run, state))

        attempts = 0
        while (
            state["analysis_result"] is not None
            and not state["analysis_result"].validated
            and attempts < MAX_ANALYST_RETRIES
        ):
            state.update(run_node("analyst", analyst_agent.run, state))
            attempts += 1

        result = state["analysis_result"]
        if result is not None and result.validated:
            state.update(run_node("visualization", visualization_agent.run, state))
        elif result is not None:
            state["errors"] = [
                *state["errors"],
                AgentError(
                    node="analyst",
                    message="Narrative failed numeric validation after retries: "
                    + "; ".join(result.validation_notes),
                    severity="warning",
                    ts=datetime.now(timezone.utc).isoformat(),
                ),
            ]
        st.rerun()

    theme.render_last_error(state)

    result = state["analysis_result"]
    if result is not None and not result.validated:
        st.warning(
            "The last answer couldn't be validated against the data and was not shown: "
            + "; ".join(result.validation_notes)
        )
