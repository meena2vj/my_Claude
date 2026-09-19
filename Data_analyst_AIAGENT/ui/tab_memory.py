"""Tab: long-term chat/session memory, browsable across app restarts.
Backed by SQLite (`services/memory_service.py`) -- a session's turns
persist independently of `st.session_state`, so pasting a past session ID
here works even after the app process has restarted.
"""

import streamlit as st

from graph.state import AgentState, ChatTurn
from services import memory_service


def render(state: AgentState) -> None:
    st.subheader("Memory")
    st.caption("Persistent chat history across sessions, keyed by Session ID.")
    st.caption(f"Current session: `{state['session_id']}`")

    current_turns = memory_service.fetch_relevant_turns(state["session_id"], limit=200)
    st.markdown(f"**{len(current_turns)}** turn(s) saved for this session so far.")

    st.markdown("---")
    st.markdown("#### Browse a session")

    sessions = memory_service.list_sessions()
    if sessions:
        with st.expander(f"Recent sessions ({len(sessions)})"):
            for s in sessions:
                st.markdown(f"- `{s['session_id']}` — last seen {s['last_seen_at']}")

    lookup_id = st.text_input("Session ID to view", value=state["session_id"]).strip()

    if not lookup_id:
        return

    if not memory_service.session_exists(lookup_id):
        st.warning("No memory found for that session ID yet.")
        return

    turns = memory_service.fetch_relevant_turns(lookup_id, limit=200)
    if not turns:
        st.caption("That session has no saved turns yet.")
        return

    st.markdown(f"#### Transcript for `{lookup_id}`")
    for turn in turns:
        with st.chat_message(turn["role"]):
            st.markdown(turn["content"])
            st.caption(turn["ts"])

    if lookup_id != state["session_id"]:
        if st.button("Resume this conversation into the current session"):
            restored = [
                ChatTurn(role=t["role"], content=t["content"], ts=t["ts"]) for t in turns
            ]
            state["conversation_history"] = [*state["conversation_history"], *restored]
            st.success("Past turns loaded into this session's Ask Your Data conversation history.")
            st.rerun()
