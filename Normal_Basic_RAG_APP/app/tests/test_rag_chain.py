from unittest.mock import MagicMock, patch

import groq
import httpx

import rag_chain
from retriever import RetrievalResult


def make_result(text: str, source_file: str = "doc.pdf", page_number: int = 1, score: float = 0.9) -> RetrievalResult:
    return RetrievalResult(chunk_id="chunk_00000", source_file=source_file, page_number=page_number, text=text, score=score)


def test_build_context_block_includes_source_and_page():
    results = [make_result("Revenue grew 12%.", source_file="report.pdf", page_number=4)]

    context = rag_chain.build_context_block(results)

    assert "[Source: report.pdf, page 4]" in context
    assert "Revenue grew 12%." in context


def test_build_context_block_empty_results_returns_empty_string():
    assert rag_chain.build_context_block([]) == ""


def test_build_user_prompt_includes_context_and_question():
    results = [make_result("Revenue grew 12%.")]

    prompt = rag_chain.build_user_prompt("How much did revenue grow?", results)

    assert "Revenue grew 12%." in prompt
    assert "How much did revenue grow?" in prompt


def test_build_user_prompt_notes_missing_context_when_no_results():
    prompt = rag_chain.build_user_prompt("Unanswerable question?", [])

    assert "no relevant context was retrieved" in prompt
    assert "Unanswerable question?" in prompt


def test_generate_answer_empty_question_returns_error_without_api_call():
    with patch.object(rag_chain.groq, "Groq") as mock_groq:
        answer = rag_chain.generate_answer("   ", [make_result("Some context.")])

    assert answer.error == "Please enter a question."
    mock_groq.assert_not_called()


def test_generate_answer_no_results_returns_insufficient_context_without_api_call():
    with patch.object(rag_chain.groq, "Groq") as mock_groq:
        answer = rag_chain.generate_answer("What is the revenue?", [])

    assert answer.answer == rag_chain.INSUFFICIENT_CONTEXT_MESSAGE
    assert answer.error is None
    mock_groq.assert_not_called()


def test_generate_answer_missing_api_key_returns_error(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", None)

    with patch.object(rag_chain.groq, "Groq") as mock_groq:
        answer = rag_chain.generate_answer("What is the revenue?", [make_result("Revenue grew 12%.")])

    assert answer.error is not None
    assert "GROQ_API_KEY" in answer.error
    mock_groq.assert_not_called()


def test_generate_answer_calls_groq_and_returns_grounded_text(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", "test-key")

    message = MagicMock(content="Revenue grew 12% [report.pdf, page 4].")
    choice = MagicMock(message=message)
    mock_response = MagicMock(choices=[choice])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(rag_chain.groq, "Groq", return_value=mock_client):
        answer = rag_chain.generate_answer("How much did revenue grow?", [make_result("Revenue grew 12%.", source_file="report.pdf", page_number=4)])

    assert answer.error is None
    assert "Revenue grew 12%" in answer.answer
    assert answer.answer_token_count > 0
    assert answer.latency_seconds >= 0.0

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == rag_chain.GROQ_MODEL
    assert call_kwargs["temperature"] == rag_chain.GENERATION_TEMPERATURE
    assert call_kwargs["messages"][0] == {"role": "system", "content": rag_chain.SYSTEM_PROMPT}


def test_generate_answer_handles_authentication_error_gracefully(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", "bad-key")

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(401, request=request)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.AuthenticationError("invalid key", response=response, body=None)

    with patch.object(rag_chain.groq, "Groq", return_value=mock_client):
        answer = rag_chain.generate_answer("A question?", [make_result("Some context.")])

    assert answer.answer == ""
    assert answer.error == "Invalid Groq API key."


def test_generate_answer_handles_rate_limit_error_gracefully(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", "test-key")

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.RateLimitError("too many requests", response=response, body=None)

    with patch.object(rag_chain.groq, "Groq", return_value=mock_client):
        answer = rag_chain.generate_answer("A question?", [make_result("Some context.")])

    assert answer.answer == ""
    assert "Rate limited" in answer.error


def test_generate_answer_handles_connection_error_gracefully(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", "test-key")

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.APIConnectionError(request=request)

    with patch.object(rag_chain.groq, "Groq", return_value=mock_client):
        answer = rag_chain.generate_answer("A question?", [make_result("Some context.")])

    assert answer.answer == ""
    assert "Could not connect" in answer.error


def test_generate_answer_handles_generic_api_status_error_gracefully(monkeypatch):
    monkeypatch.setattr(rag_chain, "GROQ_API_KEY", "test-key")

    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(500, request=request)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = groq.APIStatusError("server error", response=response, body=None)

    with patch.object(rag_chain.groq, "Groq", return_value=mock_client):
        answer = rag_chain.generate_answer("A question?", [make_result("Some context.")])

    assert answer.answer == ""
    assert "Groq API error" in answer.error
