"""Read-only conversational Q&A layer — CLAUDE.md §2.2 and §15.

This is the only place in the prototype an LLM is called. It is deliberately
narrow: it cannot run an assessment, cannot approve or reject anything, and
cannot read anything except the AssessmentReport records the deterministic
pipeline already computed and persisted to SQLite. It narrates; it does not
decide.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request

from app.db import list_runs, save_qa

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-haiku-4.5"
PROMPT_VERSION = "qa-v1"

SYSTEM_PROMPT = """You are a read-only reporting assistant for a clinical trial \
supply chain risk system. You may use ONLY the JSON assessment records given \
below, which a separate deterministic pipeline already computed and persisted. \
Rules, no exceptions:
1. Never state a site, number, or fact that is not present in the records below.
2. Never claim you can approve, reject, release, cancel, or modify anything - \
you can only describe what has already happened.
3. If asked about a site with no record below, say plainly that no assessment \
has been run for it yet and suggest running one from the dashboard.
4. Every factual claim must cite its site_id and request_id.
5. Answer in 4 sentences or fewer."""


class QAUnavailable(Exception):
    pass


def answer_question(question: str, limit: int = 20) -> dict:
    records = list_runs(limit)
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise QAUnavailable("No LLM API key configured (OPENROUTER_API_KEY).")

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Assessment records (most recent {len(records)} runs):\n"
                    f"{json.dumps(records, default=str)}\n\nQuestion: {question}"
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
    except urllib.error.URLError as exc:
        raise QAUnavailable(f"LLM call failed: {exc}") from exc
    latency_ms = round((time.perf_counter() - start) * 1000, 2)

    if "choices" not in body:
        raise QAUnavailable(body.get("error", {}).get("message", "LLM returned no answer."))

    answer = body["choices"][0]["message"]["content"].strip()
    usage = body.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")

    known_sites = {r["site_id"] for r in records}
    mentioned_sites = set(re.findall(r"\bIND\d{3,}\b", answer))
    unverified = sorted(mentioned_sites - known_sites)

    grounded_on = [r["request_id"] for r in records]
    save_qa(
        question, answer, grounded_on,
        model=MODEL, prompt_version=PROMPT_VERSION,
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )

    return {
        "answer": answer,
        "grounded_on_request_ids": grounded_on,
        "unverified_site_ids": unverified,
        "model": MODEL,
        "prompt_version": PROMPT_VERSION,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms,
    }
