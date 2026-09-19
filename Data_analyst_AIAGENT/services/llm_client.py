"""The only call-site in the codebase allowed to talk to an LLM (OpenRouter,
via the OpenAI-compatible `openai` SDK). Non-streaming: every response is
validated before it reaches the UI. A missing API key or any provider error
degrades to `LLMResult(error=...)` -- it never raises into a node.

This is also the single instrumentation point for every LLM call: an OTel
span, Prometheus counters/histograms, a trace_store row, and (if configured)
a Langfuse generation are all recorded here, so individual nodes never
reimplement instrumentation.
"""

import time
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from config.logging_config import get_logger
from config.settings import (
    GENERATION_MAX_TOKENS,
    GENERATION_TEMPERATURE,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)
from observability import langfuse_hook, trace_store
from observability.metrics import record_llm_call
from observability.otel_setup import start_span

logger = get_logger(__name__)


@dataclass
class LLMResult:
    text: str | None
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_seconds: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.text is not None


_client: OpenAI | None = None


def _get_client() -> OpenAI | None:
    global _client
    if not OPENROUTER_API_KEY:
        return None
    if _client is None:
        _client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=OPENROUTER_API_KEY)
    return _client


def _record(
    *, node_name: str, trace_id: str, user_prompt: str, latency: float, result: LLMResult
) -> None:
    record_llm_call(
        node_name, latency, result.ok, result.prompt_tokens, result.completion_tokens
    )
    trace_store.log_event(
        trace_id=trace_id,
        node=node_name,
        event_type="llm_call",
        status="ok" if result.ok else "error",
        llm_model=result.model,
        llm_prompt_tokens=result.prompt_tokens,
        llm_completion_tokens=result.completion_tokens,
        input_summary=user_prompt[:280],
        output_summary=(result.text or "")[:280],
        latency_seconds=latency,
        error_message=result.error,
    )
    langfuse_hook.log_llm_call(
        trace_id=trace_id,
        node=node_name,
        model=result.model,
        input_text=user_prompt,
        output_text=result.text,
        ok=result.ok,
    )


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    node_name: str,
    trace_id: str,
    temperature: float = GENERATION_TEMPERATURE,
    max_tokens: int = GENERATION_MAX_TOKENS,
) -> LLMResult:
    with start_span(f"llm_call:{node_name}", node=node_name, trace_id=trace_id):
        client = _get_client()
        if client is None:
            result = LLMResult(
                text=None, model=OPENROUTER_MODEL, error="OPENROUTER_API_KEY is not configured."
            )
            _record(
                node_name=node_name, trace_id=trace_id, user_prompt=user_prompt,
                latency=0.0, result=result,
            )
            return result

        start = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=OPENROUTER_MODEL,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except AuthenticationError as exc:
            logger.error(f"llm_auth_error node={node_name} trace={trace_id}: {exc}")
            result = LLMResult(
                text=None, model=OPENROUTER_MODEL, error=f"Authentication failed: {exc}"
            )
        except RateLimitError as exc:
            logger.error(f"llm_rate_limit node={node_name} trace={trace_id}: {exc}")
            result = LLMResult(text=None, model=OPENROUTER_MODEL, error=f"Rate limited: {exc}")
        except APIConnectionError as exc:
            logger.error(f"llm_connection_error node={node_name} trace={trace_id}: {exc}")
            result = LLMResult(
                text=None, model=OPENROUTER_MODEL, error=f"Connection error: {exc}"
            )
        except APIStatusError as exc:
            logger.error(f"llm_status_error node={node_name} trace={trace_id}: {exc}")
            result = LLMResult(
                text=None, model=OPENROUTER_MODEL, error=f"API error ({exc.status_code}): {exc}"
            )
        except Exception as exc:  # noqa: BLE001 - final guard, an LLM call must never crash a node
            logger.exception(f"llm_unexpected_error node={node_name} trace={trace_id}")
            result = LLMResult(text=None, model=OPENROUTER_MODEL, error=str(exc))
        else:
            latency = time.monotonic() - start
            choice = response.choices[0]
            usage = response.usage
            logger.info(f"llm_call node={node_name} trace={trace_id} latency={latency:.2f}s")
            result = LLMResult(
                text=choice.message.content,
                model=OPENROUTER_MODEL,
                prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
                latency_seconds=latency,
            )
            _record(
                node_name=node_name, trace_id=trace_id, user_prompt=user_prompt,
                latency=latency, result=result,
            )
            return result

        latency = time.monotonic() - start
        _record(
            node_name=node_name, trace_id=trace_id, user_prompt=user_prompt,
            latency=latency, result=result,
        )
        return result
