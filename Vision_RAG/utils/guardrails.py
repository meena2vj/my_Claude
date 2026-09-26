"""Prompt-injection heuristics, OCR-junk detection, and grounding checks.

Implements CLAUDE.md's Guardrails section and Required Testing Set: queries
and OCR-derived chunks are both treated as untrusted input and scanned for
instruction-override, role hijacking, policy-bypass, context-confusion, and
false-authority attempts before they can influence retrieval or generation.
Chunks with low OCR confidence are separately flagged as potential "OCR junk
contamination" so noisy scan artifacts never get treated as authoritative
evidence. Detections are logged to the audit trail.
"""

import re
from dataclasses import dataclass, field

from config import GROUNDING_MIN_OVERLAP_RATIO, OCR_MIN_CONFIDENCE
from utils.helpers import audit_log, tokenize_words

# Each category maps to regexes for one CLAUDE.md test-set scenario.
_INJECTION_PATTERNS: dict[str, list[str]] = {
    "instruction_override": [
        r"ignore\s+(all|any|the)?\s*(previous|prior|above|earlier)\s+(instructions|rules|prompts?|context)",
        r"disregard\s+(all|any|the)?\s*(previous|prior|above|earlier)\s+(instructions|rules|prompts?)",
        r"reveal\s+(the\s+)?(hidden|system)\s+(prompt|instructions|context)",
        r"forget\s+(everything|all)\s+(you\s+)?(were\s+told|above)",
        r"ignore\s+all\s+previous\s+instructions",
    ],
    "role_hijacking": [
        r"you\s+are\s+now\s+(the\s+|an?\s+)?(admin|administrator|root|system|developer|unrestricted)",
        r"act\s+as\s+(the\s+)?(admin|administrator|root|system)",
        r"bypass\s+(the\s+)?(safeguards|safety|restrictions|filters|guardrails)",
        r"i\s+am\s+(the\s+)?(admin|administrator|developer)[,.]?\s*(bypass|override|disable)",
    ],
    "policy_bypass": [
        r"ignore\s+(the\s+)?safety\s+rules",
        r"provide\s+unsupported\s+claims",
        r"answer\s+without\s+(any\s+)?evidence",
        r"do\s+not\s+cite\s+sources",
        r"answer\s+with\s+the\s+opposite\s+of\s+the\s+truth",
        r"no\s+matter\s+(what|the\s+(rules|policy|policies))",
        r"answer\s+even\s+if\s+(it'?s\s+)?(false|wrong|unsupported)",
    ],
    "context_confusion": [
        r"(use|using)\s+(your|internal)\s+(hidden\s+)?(training\s+data|memory|knowledge)(\s+instead)?",
        r"answer\s+using\s+(unrelated|other|different)\s+(docs|documents|files)",
        r"use\s+(your\s+)?hidden\s+memory",
        r"ignore\s+(these|the|those)\s+(documents?|docs|files)",
    ],
    "false_authority": [
        r"the\s+(legal|management|compliance|executive)\s+(department|team)?\s*confirms?",
        r"(this|it)\s+is\s+(officially\s+)?(confirmed|verified)\s+by\s+(the\s+)?(legal|management|authority)",
        r"according\s+to\s+(an?\s+)?(unnamed|anonymous|senior)\s+(official|authority|source)",
        r"trust\s+this\s+(claim|statement)\s+because\s+(it'?s|it\s+is)\s+(official|authoritative)",
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

    `source` is metadata for the audit log only (e.g. "query" or a file name)
    — detection logic is identical for user queries and OCR'd content, since
    both are untrusted input per CLAUDE.md's Guardrails section.
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


def is_ocr_junk(chunk, min_confidence: float = OCR_MIN_CONFIDENCE) -> bool:
    """Flag chunks whose OCR confidence is too low to trust as evidence.

    Handles the "OCR junk contamination" test-set scenario: low-quality
    scanned text with random tokens should not be prioritized by retrieval
    or treated as authoritative by generation.
    """
    return 0.0 < chunk.ocr_confidence < min_confidence


def scan_chunks(chunks: list) -> list:
    """Mark each chunk's `is_suspicious` flag in place based on injection and
    OCR-junk scanning.

    Handles the "adversarial document instruction injection", "retrieval
    poisoning", and "OCR junk contamination" test-set scenarios: text that
    tries to instruct the model, or noisy scan artifacts, are flagged and
    never treated as authoritative context.
    """
    for chunk in chunks:
        verdict = detect_injection(chunk.text, source=f"doc:{chunk.source_file}")
        junk = is_ocr_junk(chunk)
        if junk:
            audit_log(
                "ocr_junk_contamination_flagged",
                {"source_file": chunk.source_file, "page_number": chunk.page_number, "ocr_confidence": chunk.ocr_confidence},
            )
        chunk.is_suspicious = verdict.is_flagged or junk
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
