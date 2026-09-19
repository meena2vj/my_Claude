"""Tab: editable email draft summarizing analysis + KPIs + insights."""

import streamlit as st

from agents import email_agent
from graph.node_runner import run_node
from graph.state import AgentState, EmailDraft
from ui import theme


def render(state: AgentState) -> None:
    st.subheader("Email")
    if state["insights"] is None:
        st.info("Generate insights first.")
        return

    theme.render_last_error(state)

    if state["email_draft"] is None:
        if st.button("Generate email draft", type="primary"):
            state.update(run_node("email", email_agent.run, state))
            st.rerun()
        st.caption("No email draft generated yet.")
        return

    draft = state["email_draft"]
    subject = st.text_input("Subject", value=draft.subject)
    body = st.text_area("Body", value=draft.body, height=320)
    if st.button("Save edits"):
        state["email_draft"] = EmailDraft(subject=subject, body=body, editable=True)
        st.success("Email draft updated.")
