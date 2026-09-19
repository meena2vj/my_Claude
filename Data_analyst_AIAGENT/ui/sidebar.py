"""Sidebar: workflow progress, session info, KPI summary cards."""

import streamlit as st

from graph.state import AgentState, ChatTurn
from services import memory_service
from ui.theme import kpi_card

STAGES = [
    ("Business Context", lambda s: bool(s["problem_statement"].strip() and s["kpis"])),
    ("Data Upload", lambda s: s["raw_data"] is not None),
    ("Data Quality", lambda s: s["quality_report"] is not None),
    ("Data Cleaning", lambda s: s["clean_data"] is not None),
    ("Ask Your Data", lambda s: s["analysis_result"] is not None),
    ("Dashboard", lambda s: bool(s["charts"])),
    ("Insights", lambda s: s["insights"] is not None),
    ("PDF Report", lambda s: s["report_path"] is not None),
    ("Email", lambda s: s["email_draft"] is not None),
]


def render(state: AgentState) -> None:
    with st.sidebar:
        st.markdown("### Workflow Progress")
        completed = 0
        for label, check in STAGES:
            done = check(state)
            completed += int(done)
            icon = "✅" if done else "⬜"
            st.markdown(f"{icon} {label}")
        st.progress(completed / len(STAGES))

        st.markdown("---")
        st.markdown("### Session")
        st.caption(f"Session ID: `{state['session_id']}`")
        st.caption("Copy this ID to resume your session later, on this or any other restart.")

        resume_id = st.text_input("Resume a prior session", placeholder="paste session ID", key="resume_session_id")
        if st.button("Resume", key="resume_session_button") and resume_id.strip():
            resume_id = resume_id.strip()
            if not memory_service.session_exists(resume_id):
                st.error("No saved memory found for that session ID.")
            else:
                turns = memory_service.fetch_relevant_turns(resume_id, limit=200)
                state["session_id"] = resume_id
                state["conversation_history"] = [
                    ChatTurn(role=t["role"], content=t["content"], ts=t["ts"]) for t in turns
                ]
                st.success(f"Resumed session `{resume_id}` ({len(turns)} past turn(s) loaded).")
                st.rerun()

        st.markdown("---")
        st.markdown("### KPIs in scope")
        if state["kpis"]:
            for kpi in state["kpis"]:
                st.markdown(
                    kpi_card(kpi.name, kpi.target or "—"),
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No KPIs defined yet.")
