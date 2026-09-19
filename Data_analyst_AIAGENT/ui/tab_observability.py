"""Tab: current-run trace table, latency/token charts, KPI tiles, and a
cross-run comparison table. Reads directly off the in-process Prometheus
`REGISTRY` and the SQLite trace log -- no external Grafana/Prometheus
server required, so this works standalone on Hugging Face Spaces.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from prometheus_client import generate_latest

from graph.state import AgentState
from observability import langfuse_hook, trace_store
from observability.metrics import REGISTRY
from ui.theme import kpi_card


def _registry_totals() -> dict:
    totals = {"latency": 0.0, "llm_calls": 0, "errors": 0, "successes": 0}
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if sample.name == "agent_node_latency_seconds_sum":
                totals["latency"] += sample.value
            elif sample.name == "agent_llm_calls_total":
                totals["llm_calls"] += sample.value
            elif sample.name == "agent_node_errors_total":
                totals["errors"] += sample.value
            elif sample.name == "agent_node_success_total":
                totals["successes"] += sample.value
    return totals


def render(state: AgentState) -> None:
    st.subheader("Observability & Traceability")
    st.caption(f"Trace ID: `{state['trace_id']}`")

    events = trace_store.fetch_events_for_trace(state["trace_id"])
    totals = _registry_totals()
    total_runs = totals["errors"] + totals["successes"]
    success_rate = f"{(totals['successes'] / total_runs * 100):.0f}%" if total_runs else "—"

    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card("Total node latency", f"{totals['latency']:.2f}s"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card("LLM calls", int(totals["llm_calls"])), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card("Node errors", int(totals["errors"])), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card("Success rate", success_rate), unsafe_allow_html=True)

    st.markdown("---")

    if not events:
        st.info("No trace events recorded yet for this run. Progress through the workflow to populate this tab.")
        return

    df = pd.DataFrame(events)

    st.markdown("#### Current-run trace")
    st.dataframe(
        df[["ts", "node", "event_type", "tool_name", "llm_model", "latency_seconds", "status"]],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### Latency per node")
    latency_df = df.groupby("node", as_index=False)["latency_seconds"].sum()
    st.plotly_chart(
        px.bar(latency_df, x="node", y="latency_seconds", labels={"latency_seconds": "seconds"}),
        use_container_width=True,
    )

    llm_events = df[df["event_type"] == "llm_call"].copy()
    if not llm_events.empty:
        st.markdown("#### Cumulative token usage")
        llm_events["total_tokens"] = (
            llm_events["llm_prompt_tokens"].fillna(0) + llm_events["llm_completion_tokens"].fillna(0)
        )
        llm_events["cumulative_tokens"] = llm_events["total_tokens"].cumsum()
        st.plotly_chart(
            px.line(llm_events, x="ts", y="cumulative_tokens", markers=True),
            use_container_width=True,
        )

    st.markdown("---")
    st.markdown("#### Cross-run comparison")
    recent = trace_store.fetch_recent_traces()
    if recent:
        st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
    else:
        st.caption("No other runs recorded yet.")

    if langfuse_hook.is_enabled():
        st.caption(f"Langfuse tracing is enabled — search for trace `{state['trace_id']}` in your Langfuse project.")

    with st.expander("Raw Prometheus metrics"):
        st.code(generate_latest(REGISTRY).decode(), language="text")
