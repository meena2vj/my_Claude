"""Prompt construction and grounded answer generation via the Groq API."""

from dataclasses import dataclass

import groq

from config import (
    GENERATION_MAX_TOKENS,
    GENERATION_TEMPERATURE,
    GROQ_API_KEY,
    GROQ_MODEL,
    INSUFFICIENT_CONTEXT_MESSAGE,
    SYSTEM_PROMPT,
)
from retriever import RetrievalResult
from utils import count_tokens_approx, timed


@dataclass
class RagAnswer:
    answer: str
    latency_seconds: float
    answer_token_count: int
    error: str | None = None


def build_context_block(results: list[RetrievalResult]) -> str:
    if not results:
        return ""
    parts = [f"[Source: {r.source_file}, page {r.page_number}]\n{r.text}" for r in results]
    return "\n\n".join(parts)


def build_user_prompt(question: str, results: list[RetrievalResult]) -> str:
    context = build_context_block(results)
    if not context:
        return f"Question: {question}\n\nContext: (no relevant context was retrieved)"
    return f"Context:\n{context}\n\nQuestion: {question}"


def generate_answer(question: str, results: list[RetrievalResult]) -> RagAnswer:
    """Generate a grounded answer from retrieved context only, via Groq.

    Never calls the API for an empty question or when no context was
    retrieved — both are handled locally per the "insufficient information"
    generation rule.
    """
    if not question or not question.strip():
        return RagAnswer(answer="", latency_seconds=0.0, answer_token_count=0, error="Please enter a question.")

    if not results:
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
    return RagAnswer(
        answer=answer_text,
        latency_seconds=timer.elapsed_seconds,
        answer_token_count=count_tokens_approx(answer_text),
    )
