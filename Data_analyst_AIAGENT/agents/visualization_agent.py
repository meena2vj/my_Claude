"""Node: build a Plotly chart grounded in `analysis_result`."""

import io

import pandas as pd

from graph.state import AgentState, ChartSpec
from observability import trace_store
from observability.metrics import record_tool_call
from tools.chart_builders import build_chart


def run(state: AgentState) -> dict:
    result = state["analysis_result"]
    if result is None:
        return {"status": "awaiting_user"}

    if any(c.question == state["user_question"] for c in state["charts"]):
        return {"status": "in_progress"}

    result_table = pd.read_json(io.StringIO(result.result_table_json), orient="records")
    try:
        chart_type, fig = build_chart(result_table, title=result.plan_summary)
    except Exception:
        record_tool_call("build_chart", ok=False)
        raise
    record_tool_call("build_chart", ok=True)
    trace_store.log_event(
        trace_id=state["trace_id"], node="visualization", event_type="tool_call", status="ok",
        tool_name="build_chart", output_summary=chart_type,
    )
    chart = ChartSpec(
        chart_type=chart_type,
        plotly_json=fig.to_json(),
        question=state["user_question"],
        title=result.plan_summary,
    )
    return {"charts": [*state["charts"], chart], "status": "in_progress"}
