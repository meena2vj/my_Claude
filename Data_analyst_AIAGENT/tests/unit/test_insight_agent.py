import pandas as pd

import agents.insight_agent as insight_agent
from graph.state import AnalysisResult, ContextChunk, new_state
from services.llm_client import LLMResult


def _state_with_result(chunks=None):
    state = new_state("s1", "t1")
    state["problem_statement"] = "Understand regional revenue."
    result_table = pd.DataFrame({"region": ["N", "S"], "revenue": [400, 200]})
    state["analysis_result"] = AnalysisResult(
        kpi_matched="revenue",
        plan_summary="Aggregated 'revenue' by 'region'.",
        result_table_json=result_table.to_json(orient="records"),
        narrative="North led with 400 in revenue.",
        validated=True,
    )
    if chunks:
        state["business_context_chunks"] = chunks
    return state


def test_run_awaits_user_without_analysis():
    state = new_state("s1", "t1")
    assert insight_agent.run(state)["status"] == "awaiting_user"


def test_run_accepts_valid_data_derived_bullet(mocker):
    state = _state_with_result()
    mocker.patch.object(
        insight_agent,
        "call_llm",
        return_value=LLMResult(
            text=(
                "FACTS:\n- North led with 400 in revenue. [data-derived]\n"
                "RECOMMENDATIONS:\n- Investigate South's lower revenue of 200. [data-derived]\n"
                "TRENDS:\n- North is outperforming South.\n"
                "ANOMALIES:\n"
            ),
            model="test-model",
        ),
    )
    result = insight_agent.run(state)
    insights = result["insights"]
    assert len(insights.facts) == 1
    assert insights.facts[0].tag == "data-derived"
    assert len(insights.recommendations) == 1
    assert insights.trends == ["North is outperforming South."]


def test_run_drops_fabricated_data_derived_bullet(mocker):
    state = _state_with_result()
    mocker.patch.object(
        insight_agent,
        "call_llm",
        return_value=LLMResult(
            text=(
                "FACTS:\n- North led with 999999 in revenue. [data-derived]\n"
                "RECOMMENDATIONS:\nTRENDS:\nANOMALIES:\n"
            ),
            model="test-model",
        ),
    )
    result = insight_agent.run(state)
    insights = result["insights"]
    assert all(f.tag == "data-derived" for f in insights.facts)
    assert "999999" not in " ".join(f.text for f in insights.facts)


def test_run_accepts_cited_bullet_from_retrieved_chunk(mocker):
    chunk = ContextChunk(
        chunk_id="c1",
        doc_id="d1",
        filename="strategy.pdf",
        page=2,
        text="Focus on the north region growth.",
        token_count=6,
    )
    state = _state_with_result(chunks=[chunk])
    mocker.patch.object(insight_agent, "retrieve", return_value=[chunk])
    mocker.patch.object(
        insight_agent,
        "call_llm",
        return_value=LLMResult(
            text=(
                "FACTS:\n- North led with 400 in revenue. [data-derived]\n"
                "RECOMMENDATIONS:\n- Prioritize the north region per strategy guidance. "
                "[cited: strategy.pdf p.2]\nTRENDS:\nANOMALIES:\n"
            ),
            model="test-model",
        ),
    )
    result = insight_agent.run(state)
    insights = result["insights"]
    assert insights.recommendations[0].tag == "cited"
    assert insights.recommendations[0].citation.filename == "strategy.pdf"


def test_run_rejects_cited_bullet_with_unknown_filename(mocker):
    state = _state_with_result()
    mocker.patch.object(insight_agent, "retrieve", return_value=[])
    mocker.patch.object(
        insight_agent,
        "call_llm",
        return_value=LLMResult(
            text=(
                "FACTS:\n- North led with 400 in revenue. [data-derived]\n"
                "RECOMMENDATIONS:\n- Do something. [cited: madeup.pdf p.9]\nTRENDS:\nANOMALIES:\n"
            ),
            model="test-model",
        ),
    )
    result = insight_agent.run(state)
    assert result["insights"].recommendations == []
