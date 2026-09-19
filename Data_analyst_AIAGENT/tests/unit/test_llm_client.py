from types import SimpleNamespace

import services.llm_client as llm_client
from openai import AuthenticationError


def _fake_response(text: str = "hello"):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def test_call_llm_without_api_key_returns_graceful_error(monkeypatch):
    monkeypatch.setattr(llm_client, "OPENROUTER_API_KEY", None)
    monkeypatch.setattr(llm_client, "_client", None)
    result = llm_client.call_llm("system", "user", node_name="test", trace_id="t1")
    assert not result.ok
    assert "not configured" in result.error


def test_call_llm_success_returns_text_and_token_counts(monkeypatch, mocker):
    monkeypatch.setattr(llm_client, "OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(llm_client, "_client", None)

    fake_client = mocker.Mock()
    fake_client.chat.completions.create.return_value = _fake_response("the answer")
    mocker.patch.object(llm_client, "OpenAI", return_value=fake_client)

    result = llm_client.call_llm("system", "user", node_name="test", trace_id="t1")

    assert result.ok
    assert result.text == "the answer"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 5


def test_call_llm_handles_authentication_error(monkeypatch, mocker):
    monkeypatch.setattr(llm_client, "OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(llm_client, "_client", None)

    fake_client = mocker.Mock()
    fake_client.chat.completions.create.side_effect = AuthenticationError(
        message="bad key", response=mocker.Mock(status_code=401), body=None
    )
    mocker.patch.object(llm_client, "OpenAI", return_value=fake_client)

    result = llm_client.call_llm("system", "user", node_name="test", trace_id="t1")

    assert not result.ok
    assert "Authentication failed" in result.error
