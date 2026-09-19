"""In-process Prometheus metrics -- always readable from the Streamlit
Observability tab directly off `REGISTRY`, independent of whether the
optional `/metrics` HTTP server (`metrics_server.py`) is enabled. HF
Spaces-safe: nothing here binds a port.
"""

from prometheus_client import CollectorRegistry, Counter, Histogram

REGISTRY = CollectorRegistry()

NODE_LATENCY = Histogram(
    "agent_node_latency_seconds", "Latency per LangGraph node", ["node"], registry=REGISTRY
)
RUN_LATENCY = Histogram(
    "agent_total_run_latency_seconds", "Total latency for a full graph run", registry=REGISTRY
)
LLM_CALLS = Counter(
    "agent_llm_calls_total", "LLM calls", ["node", "status"], registry=REGISTRY
)
LLM_CALL_LATENCY = Histogram(
    "agent_llm_call_latency_seconds", "LLM call latency", ["node"], registry=REGISTRY
)
LLM_TOKENS = Counter("agent_llm_tokens_total", "LLM tokens", ["node", "kind"], registry=REGISTRY)
TOOL_CALLS = Counter("agent_tool_calls_total", "Tool calls", ["tool", "status"], registry=REGISTRY)
NODE_ERRORS = Counter("agent_node_errors_total", "Node errors", ["node"], registry=REGISTRY)
NODE_SUCCESS = Counter("agent_node_success_total", "Node successes", ["node"], registry=REGISTRY)


def record_node_run(node: str, latency_seconds: float, error: bool) -> None:
    NODE_LATENCY.labels(node=node).observe(latency_seconds)
    if error:
        NODE_ERRORS.labels(node=node).inc()
    else:
        NODE_SUCCESS.labels(node=node).inc()


def record_llm_call(
    node: str, latency_seconds: float, ok: bool, prompt_tokens: int = 0, completion_tokens: int = 0
) -> None:
    LLM_CALLS.labels(node=node, status="ok" if ok else "error").inc()
    LLM_CALL_LATENCY.labels(node=node).observe(latency_seconds)
    if ok:
        LLM_TOKENS.labels(node=node, kind="prompt").inc(prompt_tokens)
        LLM_TOKENS.labels(node=node, kind="completion").inc(completion_tokens)


def record_tool_call(tool: str, ok: bool) -> None:
    TOOL_CALLS.labels(tool=tool, status="ok" if ok else "error").inc()
