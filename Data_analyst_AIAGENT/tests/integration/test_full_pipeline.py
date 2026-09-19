"""Full LangGraph run START->END on a realistic messy fixture.

`call_llm` is mocked at each consuming agent's own module (never a real
OpenRouter call in tests) with narratives that contain no numeric tokens, so
`validate_narrative_against_result` passes deterministically regardless of
the exact aggregated figures the fixture produces.
"""

from pathlib import Path

import fitz
import pytest

from graph.build_graph import build_graph
from graph.state import KPIDefinition, new_state
from services.llm_client import LLMResult
from tools.file_validation import ValidatedFile, load_dataframe

FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "sample" / "sample_sales_with_issues.xlsx"
)

_INSIGHT_TEXT = (
    "FACTS:\n"
    "- North outperforms every other region by a wide margin [data-derived]\n"
    "- The remaining regions are much closer to one another [data-derived]\n"
    "RECOMMENDATIONS:\n"
    "- Prioritize inventory and marketing investment toward the North region [data-derived]\n"
    "TRENDS:\n"
    "- Revenue is heavily concentrated in a single region\n"
    "ANOMALIES:\n"
    "- North's revenue figure is disproportionately large compared to its peers\n"
)


def _fake_call_llm(system_prompt, user_prompt, *, node_name, trace_id, **kwargs):
    text = (
        "North is the clear leader among all regions, well ahead of the others."
        if node_name == "analyst"
        else _INSIGHT_TEXT
    )
    return LLMResult(text=text, model="mock-model", prompt_tokens=12, completion_tokens=8)


@pytest.fixture
def loaded_state():
    validated = ValidatedFile(
        path=FIXTURE_PATH,
        original_filename=FIXTURE_PATH.name,
        size_bytes=FIXTURE_PATH.stat().st_size,
        extension=".xlsx",
    )
    df, meta = load_dataframe(validated)

    state = new_state(session_id="integration-session", trace_id="integration-trace")
    state["problem_statement"] = "Understand regional revenue performance."
    state["kpis"] = [KPIDefinition(name="Revenue", definition="Total revenue by region")]
    state["raw_data"] = df
    state["raw_data_meta"] = meta
    return state


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    monkeypatch.setattr("agents.analyst_agent.call_llm", _fake_call_llm)
    monkeypatch.setattr("agents.insight_agent.call_llm", _fake_call_llm)


def test_pipeline_halts_for_cleaning_confirmation(loaded_state):
    raw_row_count = len(loaded_state["raw_data"])
    graph = build_graph()

    result = graph.invoke(loaded_state)

    assert result["status"] == "awaiting_user"
    assert result["clean_data"] is None
    assert result["cleaning_confirmed"] is False
    assert not result["errors"]

    assert result["cleaning_plan"]
    destructive = [a for a in result["cleaning_plan"] if a.destructive]
    assert destructive
    assert all(a.action_type == "drop_duplicates" for a in destructive)
    assert destructive[0].rows_before == raw_row_count
    assert destructive[0].rows_after < raw_row_count


def test_pipeline_completes_after_confirmation(loaded_state):
    raw_row_count = len(loaded_state["raw_data"])
    expected_duplicates = int(loaded_state["raw_data"].duplicated().sum())
    graph = build_graph()

    halted = graph.invoke(loaded_state)
    assert halted["status"] == "awaiting_user"

    halted["cleaning_confirmed"] = True
    halted["user_question"] = "Show revenue by region"

    final = graph.invoke(halted)

    assert final["status"] == "complete"
    assert not final["errors"]

    # Cleaning log / row-count reconciliation. The dedup step runs after
    # imputation, so it can remove more rows than were duplicates in the raw
    # data if imputed values happen to collide (e.g. a mode-filled 'region'
    # matching a median-filled 'revenue' on an already-duplicate row) --
    # reconciliation only requires it never removes fewer.
    assert final["clean_data"] is not None
    dedup_actions = [a for a in final["cleaning_log"] if a.action_type == "drop_duplicates"]
    assert dedup_actions
    assert dedup_actions[0].rows_before == raw_row_count
    assert dedup_actions[0].rows_after <= raw_row_count - expected_duplicates
    assert len(final["clean_data"]) == dedup_actions[-1].rows_after

    # Analysis passed the narrative-vs-result numeric cross-check.
    assert final["analysis_result"] is not None
    assert final["analysis_result"].validated is True

    # Insights: both facts and recommendations survived citation-tag verification.
    assert final["insights"] is not None
    assert final["insights"].facts
    assert final["insights"].recommendations

    # PDF has all 8 required sections.
    assert final["report_path"]
    doc = fitz.open(final["report_path"])
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

    # Email draft populated and grounded in the same state.
    assert final["email_draft"] is not None
    assert final["email_draft"].subject
    assert "Revenue" in final["email_draft"].body
    assert "North" in final["email_draft"].body
