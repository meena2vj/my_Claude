"""Node: profile `raw_data` and populate `quality_report`. Pure Pandas/NumPy,
no LLM -- see `tools/data_profiling.py`."""

from graph.state import AgentState
from tools.data_profiling import profile_dataframe


def run(state: AgentState) -> dict:
    if state["raw_data"] is None:
        return {"status": "awaiting_user"}
    if state["quality_report"] is not None:
        return {"status": "in_progress"}
    report = profile_dataframe(state["raw_data"])
    return {"quality_report": report, "status": "in_progress"}
