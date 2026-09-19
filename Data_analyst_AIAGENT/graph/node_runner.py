"""Shared node-execution wrapper: instrumentation + crash-safety.

`graph/build_graph.py` uses this to wrap every node for the full-pipeline
integration path. The live Streamlit app instead drives the workflow
tab-by-tab (each stage needs to pause for user input/confirmation, which a
single `graph.invoke()` call doesn't support), calling agent functions
directly from `ui/tab_*.py` -- so those call sites route through the same
`run_node` here. That keeps one instrumentation point (OTel span, Prometheus
metrics, trace_store row) and one place where an unexpected exception becomes
a state-level `AgentError` instead of a raw crash, regardless of which path
invoked the agent.
"""

import time
from collections.abc import Callable
from datetime import datetime, timezone

from config.logging_config import get_logger
from graph.state import AgentError, AgentState
from observability import trace_store
from observability.metrics import record_node_run
from observability.otel_setup import start_span

logger = get_logger(__name__)


def run_node(node_name: str, fn: Callable[[AgentState], dict], state: AgentState) -> dict:
    logger.info(f"node_start:{node_name}")
    trace_id = state["trace_id"]
    start = time.monotonic()
    with start_span(f"node:{node_name}", node=node_name, trace_id=trace_id):
        try:
            update = fn(state)
        except Exception as exc:  # noqa: BLE001 - convert to state error, never crash the caller
            latency = time.monotonic() - start
            logger.exception(f"node_error:{node_name}")
            record_node_run(node_name, latency, error=True)
            trace_store.log_event(
                trace_id=trace_id,
                node=node_name,
                event_type="node_run",
                status="error",
                latency_seconds=latency,
                error_message=str(exc),
            )
            error = AgentError(
                node=node_name,
                message=str(exc),
                severity="fatal",
                ts=datetime.now(timezone.utc).isoformat(),
            )
            return {"errors": [*state["errors"], error], "status": "error"}

        latency = time.monotonic() - start
        record_node_run(node_name, latency, error=False)
        trace_store.log_event(
            trace_id=trace_id,
            node=node_name,
            event_type="node_run",
            status="ok",
            latency_seconds=latency,
        )
        logger.info(f"node_end:{node_name}")
        return update
