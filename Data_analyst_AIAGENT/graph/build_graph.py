"""Assembles the LangGraph StateGraph: nodes + conditional edges.

Graph shape (CLAUDE.md section 11):
START -> problem_kpi -> ingestion -> quality -> cleaning -> analyst
      -> visualization -> insight -> report -> email -> END

Every non-terminal edge routes through `conditions.route_after` (fatal error
-> errors handler, awaiting user input -> halt this run, else continue).
The analyst node additionally uses `route_on_validation` to loop back on a
failed numeric cross-check, and the cleaning node uses
`route_on_confirmation` to hold for the user's destructive-action sign-off.
"""

from langgraph.graph import END, StateGraph

from agents import (
    analyst_agent,
    cleaning_agent,
    email_agent,
    ingestion_agent,
    insight_agent,
    problem_kpi_agent,
    quality_agent,
    report_agent,
    visualization_agent,
)

from config.logging_config import get_logger
from graph.conditions import (
    AWAITING_USER,
    CONTINUE,
    NODE_ERRORS,
    RETRY,
    route_after,
    route_on_confirmation,
    route_on_validation,
)
from graph.node_runner import run_node
from graph.state import AgentState

logger = get_logger(__name__)


def _wrap(node_name: str, fn):
    """Wrap a node's run() with the shared `run_node` instrumentation/crash-safety."""

    def _run(state: AgentState) -> dict:
        return run_node(node_name, fn, state)

    return _run


def _handle_errors(state: AgentState) -> dict:
    return {"status": "error"}


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("problem_kpi", _wrap("problem_kpi", problem_kpi_agent.run))
    graph.add_node("ingestion", _wrap("ingestion", ingestion_agent.run))
    graph.add_node("quality", _wrap("quality", quality_agent.run))
    graph.add_node("cleaning", _wrap("cleaning", cleaning_agent.run))
    graph.add_node("analyst", _wrap("analyst", analyst_agent.run))
    graph.add_node("visualization", _wrap("visualization", visualization_agent.run))
    graph.add_node("insight", _wrap("insight", insight_agent.run))
    graph.add_node("report", _wrap("report", report_agent.run))
    graph.add_node("email", _wrap("email", email_agent.run))
    graph.add_node("error_handler", _handle_errors)

    graph.set_entry_point("problem_kpi")

    graph.add_conditional_edges(
        "problem_kpi",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "ingestion"},
    )
    graph.add_conditional_edges(
        "ingestion",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "quality"},
    )
    graph.add_conditional_edges(
        "quality",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "cleaning"},
    )
    graph.add_conditional_edges(
        "cleaning",
        route_on_confirmation,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "analyst"},
    )
    graph.add_conditional_edges(
        "analyst",
        route_on_validation,
        {
            AWAITING_USER: END,
            RETRY: "analyst",
            NODE_ERRORS: "error_handler",
            CONTINUE: "visualization",
        },
    )
    graph.add_conditional_edges(
        "visualization",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "insight"},
    )
    graph.add_conditional_edges(
        "insight",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "report"},
    )
    graph.add_conditional_edges(
        "report",
        route_after,
        {AWAITING_USER: END, NODE_ERRORS: "error_handler", CONTINUE: "email"},
    )
    graph.add_edge("email", END)
    graph.add_edge("error_handler", END)

    return graph.compile()
