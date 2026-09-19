"""Node: assemble the downloadable PDF report."""

from graph.state import AgentState
from observability import trace_store
from observability.metrics import record_tool_call
from services.report_builder import build_pdf


def run(state: AgentState) -> dict:
    if state["insights"] is None:
        return {"status": "awaiting_user"}
    if state["report_path"] is not None:
        return {"status": "in_progress"}
    try:
        path = build_pdf(state)
    except Exception:
        record_tool_call("build_pdf", ok=False)
        raise
    record_tool_call("build_pdf", ok=True)
    trace_store.log_event(
        trace_id=state["trace_id"], node="report", event_type="tool_call", status="ok",
        tool_name="build_pdf", output_summary=path,
    )
    return {"report_path": path, "status": "in_progress"}
