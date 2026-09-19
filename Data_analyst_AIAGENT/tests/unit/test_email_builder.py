from graph.state import AnalysisResult, EmailDraft, InsightItem, InsightReport, KPIDefinition, new_state
from services.email_builder import build_email


def test_build_email_includes_kpis_and_recommendations():
    state = new_state("s1", "t1")
    state["problem_statement"] = "Understand regional revenue."
    state["kpis"] = [KPIDefinition(name="Revenue", definition="Total revenue")]
    state["analysis_result"] = AnalysisResult(
        plan_summary="Aggregated revenue by region.",
        result_table_json="[]",
        narrative="North led with 400 in revenue.",
        validated=True,
    )
    state["insights"] = InsightReport(
        facts=[InsightItem(text="North leads.", tag="data-derived")],
        recommendations=[InsightItem(text="Focus on North.", tag="data-derived")],
    )
    draft = build_email(state)
    assert isinstance(draft, EmailDraft)
    assert "Revenue" in draft.body
    assert "North leads." in draft.body
    assert "Focus on North." in draft.body
    assert draft.editable is True


def test_build_email_handles_missing_data_gracefully():
    state = new_state("s1", "t1")
    draft = build_email(state)
    assert "(no KPIs defined)" in draft.body
    assert "(no analysis run)" in draft.body
