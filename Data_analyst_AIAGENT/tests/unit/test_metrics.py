"""Unit tests for the in-process Prometheus metrics helpers."""

from observability.metrics import REGISTRY, record_llm_call, record_node_run, record_tool_call


def _sample_value(name: str, **labels) -> float | None:
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == name and all(sample.labels.get(k) == v for k, v in labels.items()):
                return sample.value
    return None


def test_record_node_run_increments_success_and_error_counters():
    before_success = _sample_value("agent_node_success_total", node="unit_test_node") or 0
    before_error = _sample_value("agent_node_errors_total", node="unit_test_node") or 0

    record_node_run("unit_test_node", 0.1, error=False)
    record_node_run("unit_test_node", 0.2, error=True)

    assert _sample_value("agent_node_success_total", node="unit_test_node") == before_success + 1
    assert _sample_value("agent_node_errors_total", node="unit_test_node") == before_error + 1


def test_record_llm_call_tracks_tokens_only_on_success():
    record_llm_call("unit_test_llm_node", 0.5, ok=True, prompt_tokens=10, completion_tokens=5)
    record_llm_call("unit_test_llm_node", 0.1, ok=False, prompt_tokens=999, completion_tokens=999)

    assert _sample_value(
        "agent_llm_calls_total", node="unit_test_llm_node", status="ok"
    ) == 1
    assert _sample_value(
        "agent_llm_calls_total", node="unit_test_llm_node", status="error"
    ) == 1
    assert _sample_value(
        "agent_llm_tokens_total", node="unit_test_llm_node", kind="prompt"
    ) == 10


def test_record_tool_call_labels_by_status():
    record_tool_call("unit_test_tool", ok=True)
    record_tool_call("unit_test_tool", ok=False)

    assert _sample_value("agent_tool_calls_total", tool="unit_test_tool", status="ok") == 1
    assert _sample_value("agent_tool_calls_total", tool="unit_test_tool", status="error") == 1
