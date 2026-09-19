"""Node: gate on `raw_data` being present.

File validation and CSV/XLSX loading happen in `ui/tab_data_upload.py` via
`tools/file_validation.py` before the graph is invoked -- this node just
confirms a validated dataset is in state before the workflow proceeds.
"""

from graph.state import AgentState


def run(state: AgentState) -> dict:
    if state["raw_data"] is None:
        return {"status": "awaiting_user"}
    return {"status": "in_progress"}
