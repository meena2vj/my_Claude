"""Node: propose a deterministic cleaning plan from the quality report, then
execute it once the user confirms (`cleaning_confirmed=True`).

The action list itself is always produced by `tools/data_cleaning_ops.py`
(deterministic, testable without an LLM) -- per the guardrails, an LLM may
narrate a plan but must never be the thing performing or choosing the
transformation. `raw_data` is never mutated; execution always writes a copy
into `clean_data`.
"""

from graph.state import AgentState
from observability import trace_store
from observability.metrics import record_tool_call
from tools.data_cleaning_ops import build_default_plan, execute_plan


def run(state: AgentState) -> dict:
    if state["quality_report"] is None:
        return {"status": "awaiting_user"}

    if not state["cleaning_plan"]:
        plan = build_default_plan(state["raw_data"], state["quality_report"])
        if not plan:
            return {
                "clean_data": state["raw_data"].copy(deep=True),
                "cleaning_confirmed": True,
                "status": "in_progress",
            }
        return {"cleaning_plan": plan, "status": "awaiting_user"}

    if not state["cleaning_confirmed"]:
        return {"status": "awaiting_user"}

    if state["clean_data"] is not None:
        return {"status": "in_progress"}

    try:
        clean_df, log = execute_plan(state["raw_data"], state["cleaning_plan"])
    except Exception:
        record_tool_call("execute_plan", ok=False)
        raise
    record_tool_call("execute_plan", ok=True)
    trace_store.log_event(
        trace_id=state["trace_id"], node="cleaning", event_type="tool_call", status="ok",
        tool_name="execute_plan", output_summary=f"{len(log)} actions",
    )
    return {"clean_data": clean_df, "cleaning_log": log, "status": "in_progress"}
