"""Prompt-injection heuristics and grounding checks.

Implements CLAUDE.md's Guardrails section: queries and PDF-derived chunks are
both treated as untrusted input and scanned for instruction-override, role
hijacking, and policy-bypass attempts before they can influence retrieval or
generation. Detections are logged to the audit trail.
"""

import re
from dataclasses import dataclass, field

from config import GROUNDING_MIN_OVERLAP_RATIO
from src.utils.helpers import audit_log, tokenize_words

# Each category maps to regexes for one CLAUDE.md test-set scenario.
_INJECTION_PATTERNS: dict[str, list[str]] = {
    "instruction_override": [
        r"ignore\s+(all|any|the)?\s*(previous|prior|above|earlier)\s+(instructions|rules|prompts?|context)",
        r"disregard\s+(all|any|the)?\s*(previous|prior|above|earlier)\s+(instructions|rules|prompts?)",
        r"reveal\s+(the\s+)?(hidden|system)\s+(prompt|instructions|context)",
        r"forget\s+(everything|all)\s+(you\s+)?(were\s+told|above)",
    ],
    "role_hijacking": [
        r"you\s+are\s+now\s+(the\s+)?(admin|administrator|root|system|developer)",
        r"act\s+as\s+(the\s+)?(admin|administrator|root|system)",
        r"bypass\s+(the\s+)?(safeguards|safety|restrictions|filters|guardrails)",
        r"i\s+am\s+(the\s+)?(admin|administrator|developer)[,.]?\s*(bypass|override|disable)",
    ],
    "policy_bypass": [
        r"ignore\s+(the\s+)?safety\s+rules",
        r"provide\s+unsupported\s+claims",
        r"answer\s+without\s+(any\s+)?evidence",
        r"no\s+matter\s+(what|the\s+(rules|policy|policies))",
        r"answer\s+even\s+if\s+(it'?s\s+)?(false|wrong|unsupported)",
    ],
    "context_confusion": [
        r"(use|using)\s+(your|internal)\s+(hidden\s+)?(training\s+data|memory|knowledge)(\s+instead)?",
        r"answer\s+using\s+(unrelated|other|different)\s+(docs|documents|files)",
        r"use\s+(your\s+)?hidden\s+memory",
        r"ignore\s+(these|the|those)\s+(documents?|docs|files)",
    ],
}

_COMPILED_PATTERNS: dict[str, list[re.Pattern]] = {
    category: [re.compile(p, re.IGNORECASE) for p in patterns]
    for category, patterns in _INJECTION_PATTERNS.items()
}


@dataclass
class InjectionVerdict:
    is_flagged: bool
    categories: list[str] = field(default_factory=list)
    matched_snippets: list[str] = field(default_factory=list)


def detect_injection(text: str, source: str = "query") -> InjectionVerdict:
    """Scan `text` for prompt-injection patterns.

    `source` is metadata for the audit log only (e.g. "query" or a PDF file
    name) — detection logic is identical for user queries and PDF content,
    since both are untrusted input per CLAUDE.md's Guardrails section.
    """
    if not text or not text.strip():
        return InjectionVerdict(is_flagged=False)

    categories: list[str] = []
    snippets: list[str] = []
    for category, patterns in _COMPILED_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                categories.append(category)
                snippets.append(match.group(0))
                break  # one hit per category is enough to flag it

    verdict = InjectionVerdict(is_flagged=bool(categories), categories=categories, matched_snippets=snippets)

    if verdict.is_flagged:
        audit_log(
            "prompt_injection_detected",
            {"source": source, "categories": categories, "snippets": snippets},
        )

    return verdict


def scan_chunks(chunks: list) -> list:
    """Mark each chunk's `is_suspicious` flag in place based on injection scanning.

    Handles the "PDF malicious content" and "retrieval poisoning" test-set
    scenarios: text embedded in an uploaded PDF that tries to instruct the
    model is flagged and never treated as authoritative context.
    """
    for chunk in chunks:
        verdict = detect_injection(chunk.text, source=f"pdf:{chunk.source_file}")
        chunk.is_suspicious = verdict.is_flagged
    return chunks


def check_grounding(answer: str, context_text: str, min_overlap_ratio: float = GROUNDING_MIN_OVERLAP_RATIO) -> bool:
    """Lexical-overlap sanity check: do the answer's content words actually
    appear in the retrieved context? Guards the "citation test" scenario —
    no answer should stand without matching source evidence.

    Uses a permissive threshold (fraction of answer words found in context)
    since paraphrasing is expected; this is a safety net, not a precision tool.
    """
    if not answer or not answer.strip():
        return False

    answer_words = [w for w in tokenize_words(answer) if len(w) > 3]
    if not answer_words:
        return True  # nothing substantive to verify (e.g. pure numbers/short reply)

    context_words = set(tokenize_words(context_text))
    if not context_words:
        return False

    overlap = sum(1 for w in answer_words if w in context_words)
    ratio = overlap / len(answer_words)
    return ratio >= min_overlap_ratio
