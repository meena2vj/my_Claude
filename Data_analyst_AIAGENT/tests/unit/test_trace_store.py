"""Unit tests for the SQLite trace log (schema + insert/query)."""

from observability import trace_store


def test_log_event_and_fetch_for_trace():
    trace_store.log_event(
        trace_id="t1", node="analyst", event_type="node_run", status="ok", latency_seconds=0.5
    )
    trace_store.log_event(
        trace_id="t1", node="analyst", event_type="llm_call", status="error",
        error_message="boom",
    )
    trace_store.log_event(trace_id="t2", node="ingestion", event_type="node_run", status="ok")

    events = trace_store.fetch_events_for_trace("t1")
    assert len(events) == 2
    assert {e["event_type"] for e in events} == {"node_run", "llm_call"}
    assert events[1]["error_message"] == "boom"


def test_fetch_recent_traces_counts_errors():
    trace_store.log_event(trace_id="t1", node="a", event_type="node_run", status="ok")
    trace_store.log_event(trace_id="t1", node="b", event_type="node_run", status="error")
    trace_store.log_event(trace_id="t2", node="a", event_type="node_run", status="ok")

    recent = trace_store.fetch_recent_traces()
    by_id = {r["trace_id"]: r for r in recent}
    assert by_id["t1"]["event_count"] == 2
    assert by_id["t1"]["error_count"] == 1
    assert by_id["t2"]["error_count"] == 0


def test_fetch_events_for_unknown_trace_is_empty():
    assert trace_store.fetch_events_for_trace("does-not-exist") == []
