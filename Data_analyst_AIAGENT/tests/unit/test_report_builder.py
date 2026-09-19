import fitz

from graph.state import (
    AnalysisResult,
    InsightItem,
    InsightReport,
    KPIDefinition,
    QualityReport,
    new_state,
)
from services.report_builder import build_pdf


def test_build_pdf_contains_all_required_sections():
    state = new_state("s1", "t1")
    state["problem_statement"] = "Understand regional revenue."
    state["kpis"] = [KPIDefinition(name="Revenue", definition="Total revenue")]
    state["quality_report"] = QualityReport(
        row_count=10,
        column_count=2,
        missing_by_column=[],
        duplicate_row_count=0,
        duplicate_row_percentage=0.0,
        outliers_by_column=[],
        numeric_columns=["revenue"],
        categorical_columns=["region"],
        unique_counts={"region": 3},
        invalid_value_columns=[],
        constant_columns=[],
        descriptive_stats={},
    )
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

    path = build_pdf(state)
    doc = fitz.open(path)
    text = "\n".join(page.get_text() for page in doc)
    doc.close()

    for section in [
        "Problem Statement",
        "KPIs",
        "Data Quality Summary",
        "Cleaning Summary",
        "Analysis",
        "Dashboard / Charts",
        "Key Insights",
        "Recommendations",
    ]:
        assert section in text
    assert "North leads." in text
