"""Node: capture the business problem statement and KPI definitions.

Pure state capture -- the values are collected by the Streamlit UI
(`ui/tab_business_context.py`) before the graph is invoked; this node just
validates that both are present.
"""

from graph.state import AgentState


def run(state: AgentState) -> dict:
    if not state["problem_statement"].strip() or not state["kpis"]:
        return {"status": "awaiting_user"}
    return {"status": "in_progress"}
