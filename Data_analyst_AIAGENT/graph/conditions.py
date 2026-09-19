"""Conditional-edge predicates for the LangGraph workflow."""

from graph.state import AgentState

NODE_ERRORS = "node_errors"
CONTINUE = "continue"
AWAITING_USER = "awaiting_user"
RETRY = "retry"


def route_on_error(state: AgentState) -> str:
    """Route to a shared error path if the most recent error is fatal."""
    if state["errors"] and state["errors"][-1].severity == "fatal":
        return NODE_ERRORS
    return CONTINUE


def route_after(state: AgentState) -> str:
    """General-purpose edge used after most nodes: fatal error takes
    priority, then "awaiting user input" (blocks graph progression so the
    UI can collect what's missing), otherwise continue to the next stage."""
    if state["errors"] and state["errors"][-1].severity == "fatal":
        return NODE_ERRORS
    if state["status"] == "awaiting_user":
        return AWAITING_USER
    return CONTINUE


def route_on_confirmation(state: AgentState) -> str:
    """Hold at the cleaning node until the user has confirmed the plan.
    Falls back to the general error/awaiting-user check first."""
    base = route_after(state)
    if base != CONTINUE:
        return base
    if state["cleaning_plan"] and not state["cleaning_confirmed"]:
        return AWAITING_USER
    return CONTINUE


def route_on_validation(state: AgentState) -> str:
    """Loop back into the analyst node if the narrative failed validation,
    capped by MAX_ANALYST_RETRIES to avoid infinite retries. Falls back to
    the general error/awaiting-user check first."""
    from config.settings import MAX_ANALYST_RETRIES

    base = route_after(state)
    if base != CONTINUE:
        return base

    result = state["analysis_result"]
    if result is not None and not result.validated:
        if state["retry_count"].get("analyst", 0) < MAX_ANALYST_RETRIES:
            return RETRY
        return NODE_ERRORS
    return CONTINUE
