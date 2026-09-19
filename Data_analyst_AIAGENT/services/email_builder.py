"""Deterministic email draft assembly -- template only, no LLM call, so the
email can never introduce a number or claim that isn't already validated
elsewhere in state."""

from graph.state import AgentState, EmailDraft


def build_email(state: AgentState) -> EmailDraft:
    kpi_lines = "\n".join(f"- {k.name}: {k.definition}" for k in state["kpis"]) or "(no KPIs defined)"

    result = state["analysis_result"]
    analysis_line = result.narrative if result else "(no analysis run)"

    insights = state["insights"]
    fact_lines = (
        "\n".join(f"- {f.text}" for f in insights.facts)
        if insights and insights.facts
        else "(no key findings)"
    )
    rec_lines = (
        "\n".join(f"- {r.text}" for r in insights.recommendations)
        if insights and insights.recommendations
        else "(no recommendations)"
    )

    subject = "Data Analysis Summary"
    if state["problem_statement"]:
        subject += f": {state['problem_statement'][:60]}"

    body = (
        "Hi,\n\nHere is a summary of the latest data analysis.\n\n"
        f"Problem statement:\n{state['problem_statement'] or '(not provided)'}\n\n"
        f"KPIs:\n{kpi_lines}\n\n"
        f"Analysis:\n{analysis_line}\n\n"
        f"Key findings:\n{fact_lines}\n\n"
        f"Recommended actions:\n{rec_lines}\n\n"
        "Best regards,\nData Analyst AI Agent"
    )
    return EmailDraft(subject=subject, body=body, editable=True)
