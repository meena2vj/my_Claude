"""Prompt construction and grounded answer generation via the Groq API."""

from dataclasses import dataclass

import groq

from config import (
    GENERATION_MAX_TOKENS,
    GENERATION_TEMPERATURE,
    GROQ_API_KEY,
    GROQ_MODEL,
    INJECTION_REFUSAL_MESSAGE,
    INSUFFICIENT_CONTEXT_MESSAGE,
    PROMPT_TEMPLATE_VERSION,
    SYSTEM_PROMPT,
)
from src.hybrid.fusion import FusedChunk
from src.hybrid.guardrails import check_grounding, detect_injection
from src.utils.helpers import audit_log, count_tokens_approx, timed


@dataclass
class RagAnswer:
    answer: str
    latency_seconds: float
    answer_token_count: int
    error: str | None = None
    flagged: bool = False


def _retrieval_confidence_hint(results: list[FusedChunk]) -> str:
    """Cheap retrieval-side confidence signal, passed to the LLM as a hint —
    the model still decides the final Confidence line, but grounded in how
    much the two retrievers actually agreed."""
    if not results:
        return "Low (no supporting chunks retrieved)"
    agreeing = sum(1 for r in results if r.dense_rank is not None and r.sparse_rank is not None)
    if agreeing >= 2 and results[0].dense_rank == 1 and results[0].sparse_rank is not None:
        return "High (multiple chunks confirmed by both dense and sparse retrieval)"
    if agreeing >= 1:
        return "Medium (at least one chunk confirmed by both retrieval modes)"
    return "Low (dense and sparse retrieval did not agree on any chunk)"


def build_context_block(results: list[FusedChunk]) -> str:
    """Join non-suspicious chunks into a citation-tagged context block.

    Chunks flagged by guardrails.scan_chunks as suspicious are excluded here —
    they may still be shown in the UI results panel with a warning, but never
    fed to the LLM as trusted context (defends the "PDF malicious content" and
    "retrieval poisoning" scenarios).
    """
    trusted = [r for r in results if not r.is_suspicious]
    if not trusted:
        return ""
    parts = [f"[Source: {r.source_file}, page {r.page_number}]\n{r.text}" for r in trusted]
    return "\n\n".join(parts)


def build_user_prompt(question: str, results: list[FusedChunk]) -> str:
    context = build_context_block(results)
    if not context:
        return f"Question: {question}\n\nContext: (no relevant context was retrieved)"
    hint = _retrieval_confidence_hint(results)
    return (
        f"Context:\n{context}\n\n"
        f"Retrieval confidence signal (informational only, not a source of facts): {hint}\n\n"
        f"Question: {question}"
    )


def generate_answer(question: str, results: list[FusedChunk], retrieval_mode: str = "hybrid") -> RagAnswer:
    """Generate a grounded answer from retrieved context only, via Groq.

    Refuses immediately if the question itself looks like a prompt-injection
    attempt, and re-checks the model's answer against retrieved context
    before returning it (defends the "citation test" scenario).
    """
    if not question or not question.strip():
        return RagAnswer(answer="", latency_seconds=0.0, answer_token_count=0, error="Please enter a question.")

    query_verdict = detect_injection(question, source="query")
    if query_verdict.is_flagged:
        audit_log(
            "generation_refused",
            {"reason": "query_flagged", "categories": query_verdict.categories, "retrieval_mode": retrieval_mode},
        )
        return RagAnswer(
            answer=INJECTION_REFUSAL_MESSAGE,
            latency_seconds=0.0,
            answer_token_count=count_tokens_approx(INJECTION_REFUSAL_MESSAGE),
            flagged=True,
        )

    trusted_results = [r for r in results if not r.is_suspicious]
    if not trusted_results:
        return RagAnswer(
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            latency_seconds=0.0,
            answer_token_count=count_tokens_approx(INSUFFICIENT_CONTEXT_MESSAGE),
        )

    if not GROQ_API_KEY:
        return RagAnswer(
            answer="",
            latency_seconds=0.0,
            answer_token_count=0,
            error="Missing GROQ_API_KEY. Set it in your .env file to enable answer generation.",
        )

    user_prompt = build_user_prompt(question, results)
    context_text = build_context_block(results)
    client = groq.Groq(api_key=GROQ_API_KEY)

    with timed() as timer:
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                max_tokens=GENERATION_MAX_TOKENS,
                temperature=GENERATION_TEMPERATURE,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except groq.AuthenticationError:
            return RagAnswer(answer="", latency_seconds=0.0, answer_token_count=0, error="Invalid Groq API key.")
        except groq.RateLimitError:
            return RagAnswer(
                answer="", latency_seconds=0.0, answer_token_count=0,
                error="Rate limited by the Groq API. Please try again shortly.",
            )
        except groq.APIConnectionError:
            return RagAnswer(
                answer="", latency_seconds=0.0, answer_token_count=0,
                error="Could not connect to the Groq API. Check your network connection.",
            )
        except groq.APIStatusError as exc:
            return RagAnswer(
                answer="", latency_seconds=0.0, answer_token_count=0,
                error=f"Groq API error: {exc.message}",
            )

    answer_text = response.choices[0].message.content or ""

    if not check_grounding(answer_text, context_text):
        audit_log("grounding_check_failed", {"question": question, "retrieval_mode": retrieval_mode})
        return RagAnswer(
            answer=INSUFFICIENT_CONTEXT_MESSAGE,
            latency_seconds=timer.elapsed_seconds,
            answer_token_count=count_tokens_approx(INSUFFICIENT_CONTEXT_MESSAGE),
        )

    audit_log(
        "answer_generated",
        {
            "model": GROQ_MODEL,
            "prompt_template_version": PROMPT_TEMPLATE_VERSION,
            "retrieval_mode": retrieval_mode,
            "num_sources": len(trusted_results),
            "latency_seconds": timer.elapsed_seconds,
        },
    )
    return RagAnswer(
        answer=answer_text,
        latency_seconds=timer.elapsed_seconds,
        answer_token_count=count_tokens_approx(answer_text),
    )
