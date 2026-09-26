import pandas as pd

import agents.analyst_agent as analyst_agent
from graph.state import ChatTurn, KPIDefinition, new_state
from services.llm_client import LLMResult


def _state_with_data():
    state = new_state("s1", "t1")
    state["kpis"] = [KPIDefinition(name="Revenue", definition="Total revenue")]
    state["clean_data"] = pd.DataFrame({"region": ["N", "S", "N"], "revenue": [100, 200, 300]})
    return state


def test_run_awaits_user_without_question():
    state = _state_with_data()
    result = analyst_agent.run(state)
    assert result["status"] == "awaiting_user"


def test_run_produces_validated_result_with_mocked_llm(mocker):
    state = _state_with_data()
    state["user_question"] = "How is revenue by region?"

    mocker.patch.object(
        analyst_agent,
        "call_llm",
        return_value=LLMResult(text="North led with 400 in revenue.", model="test-model"),
    )

    result = analyst_agent.run(state)
    assert result["analysis_result"].validated
    assert result["analysis_result"].kpi_matched == "revenue"
    assert "conversation_history" in result


def test_run_includes_short_term_memory_in_prompt(mocker):
    state = _state_with_data()
    state["user_question"] = "How is revenue by region?"
    state["conversation_history"] = [
        ChatTurn(role="user", content="What was revenue last quarter?", ts="t"),
        ChatTurn(role="assistant", content="Revenue last quarter was 900.", ts="t"),
    ]

    mock_call_llm = mocker.patch.object(
        analyst_agent,
        "call_llm",
        return_value=LLMResult(text="North led with 400 in revenue.", model="test-model"),
    )

    analyst_agent.run(state)

    user_prompt = mock_call_llm.call_args.args[1]
    assert "What was revenue last quarter?" in user_prompt
    assert "Revenue last quarter was 900." in user_prompt


def test_run_retries_on_fabricated_number(mocker):
    state = _state_with_data()
    state["user_question"] = "How is revenue by region?"

    mocker.patch.object(
        analyst_agent,
        "call_llm",
        return_value=LLMResult(text="North led with 999999 in revenue.", model="test-model"),
    )

    result = analyst_agent.run(state)
    assert not result["analysis_result"].validated
    assert result["retry_count"]["analyst"] == 1
    assert "conversation_history" not in result
