"""Node: draft a professional summary email."""

from graph.state import AgentState
from observability import trace_store
from observability.metrics import record_tool_call
from services.email_builder import build_email


def run(state: AgentState) -> dict:
    if state["insights"] is None:
        return {"status": "awaiting_user"}
    if state["email_draft"] is not None:
        return {"status": "complete"}
    try:
        draft = build_email(state)
    except Exception:
        record_tool_call("build_email", ok=False)
        raise
    record_tool_call("build_email", ok=True)
    trace_store.log_event(
        trace_id=state["trace_id"], node="email", event_type="tool_call", status="ok",
        tool_name="build_email", output_summary=draft.subject,
    )
    return {"email_draft": draft, "status": "complete"}
