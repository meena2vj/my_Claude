"""Node: generate facts/recommendations grounded in data + RAG business context.

Every bullet the LLM produces must be tagged `[data-derived]` (checked against
`analysis_result`'s result table, the same guardrail `analyst_agent` uses) or
`[cited: <filename> p.<page>]` (checked against an actually-retrieved business
context chunk). An untagged, unverifiable, or numerically-fabricated bullet is
dropped rather than shown -- this is the enforcement side of CLAUDE.md's
insight-citation rule.
"""

import io
import re

import pandas as pd

from graph.state import AgentState, CitationRef, InsightItem, InsightReport
from services.llm_client import call_llm
from services.rag_business_context import retrieve
from tools.analysis_ops import validate_narrative_against_result

_SYSTEM_PROMPT = (
    "You are a data analyst writing an insight summary. You are given "
    "NUMERIC_DATA (the exact, already-computed result table) and, optionally, "
    "BUSINESS_CONTEXT excerpts, each labeled with a [filename p.N] tag. "
    "Write FACTS, RECOMMENDATIONS, TRENDS and ANOMALIES sections as bullet "
    "lists. Every bullet under FACTS and RECOMMENDATIONS MUST end with "
    "exactly one tag: '[data-derived]' if the bullet's numbers come only "
    "from NUMERIC_DATA, or '[cited: <filename> p.<page>]' using one of the "
    "exact filename/page pairs given in BUSINESS_CONTEXT if the bullet is "
    "qualitative context from a document. Never invent a filename or page. "
    "TRENDS and ANOMALIES bullets need no tag. Use this exact format:\n"
    "FACTS:\n- ...\nRECOMMENDATIONS:\n- ...\nTRENDS:\n- ...\nANOMALIES:\n- ..."
)

_SECTION_PATTERN = re.compile(r"^(FACTS|RECOMMENDATIONS|TRENDS|ANOMALIES):\s*$", re.IGNORECASE)
_CITED_PATTERN = re.compile(r"\[cited:\s*(?P<filename>[^\]]+?)\s+p\.(?P<page>\d+)\]", re.IGNORECASE)
_DATA_DERIVED_PATTERN = re.compile(r"\[data-derived\]", re.IGNORECASE)


def _parse_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"FACTS": [], "RECOMMENDATIONS": [], "TRENDS": [], "ANOMALIES": []}
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = _SECTION_PATTERN.match(line)
        if header:
            current = header.group(1).upper()
            continue
        if current and line.startswith("-"):
            sections[current].append(line.lstrip("- ").strip())
    return sections


def _build_tagged_item(
    bullet: str, result_table: pd.DataFrame, chunk_lookup: dict[tuple[str, int], str]
) -> InsightItem | None:
    cited = _CITED_PATTERN.search(bullet)
    if cited:
        filename = cited.group("filename").strip()
        page = int(cited.group("page"))
        snippet = chunk_lookup.get((filename, page))
        if snippet is None:
            return None
        text = _CITED_PATTERN.sub("", bullet).strip()
        return InsightItem(
            text=text, tag="cited", citation=CitationRef(filename=filename, page=page, snippet=snippet)
        )

    if _DATA_DERIVED_PATTERN.search(bullet):
        text = _DATA_DERIVED_PATTERN.sub("", bullet).strip()
        if validate_narrative_against_result(text, result_table):
            return None
        return InsightItem(text=text, tag="data-derived")

    return None


def _validated_bullets(bullets: list[str], result_table: pd.DataFrame) -> list[str]:
    """Drop any TRENDS/ANOMALIES bullet whose numbers don't match result_table.

    These sections carry no citation tag (unlike FACTS/RECOMMENDATIONS), so
    this is their only guard against a fabricated number reaching the user.
    """
    return [b for b in bullets if not validate_narrative_against_result(b, result_table)]


def _fallback_report(result_table: pd.DataFrame, plan_summary: str) -> InsightReport:
    facts = [
        InsightItem(text=f"{plan_summary} See the result table for exact figures.", tag="data-derived")
    ]
    numeric_cols = result_table.select_dtypes(include="number").columns.tolist()
    if len(result_table) >= 2 and numeric_cols:
        value_col = numeric_cols[0]
        label_col = result_table.columns[0]
        top = result_table.iloc[0]
        bottom = result_table.iloc[-1]
        facts.append(
            InsightItem(
                text=f"'{top[label_col]}' has the highest {value_col} at {top[value_col]}.",
                tag="data-derived",
            )
        )
        facts.append(
            InsightItem(
                text=f"'{bottom[label_col]}' has the lowest {value_col} at {bottom[value_col]}.",
                tag="data-derived",
            )
        )
    return InsightReport(facts=facts, recommendations=[], trends=[], anomalies=[])


def run(state: AgentState) -> dict:
    result = state["analysis_result"]
    if result is None:
        return {"status": "awaiting_user"}
    if state["insights"] is not None:
        return {"status": "in_progress"}

    result_table = pd.read_json(io.StringIO(result.result_table_json), orient="records")
    context_chunks = retrieve(
        state["business_context_chunks"], state["problem_statement"] or state["user_question"]
    )
    chunk_lookup = {(c.filename, c.page): c.text[:280] for c in context_chunks}

    numeric_block = result_table.to_string(index=False)
    context_block = (
        "\n\n".join(f"[{c.filename} p.{c.page}] {c.text}" for c in context_chunks)
        or "(no business context documents uploaded)"
    )
    user_prompt = (
        f"PROBLEM STATEMENT: {state['problem_statement']}\n\nNUMERIC_DATA:\n{numeric_block}\n\n"
        f"BUSINESS_CONTEXT:\n{context_block}"
    )

    llm_result = call_llm(_SYSTEM_PROMPT, user_prompt, node_name="insight", trace_id=state["trace_id"])
    if not llm_result.ok:
        return {"insights": _fallback_report(result_table, result.plan_summary), "status": "in_progress"}

    sections = _parse_sections(llm_result.text)

    facts = [
        item
        for bullet in sections["FACTS"]
        if (item := _build_tagged_item(bullet, result_table, chunk_lookup)) is not None
    ]
    recommendations = [
        item
        for bullet in sections["RECOMMENDATIONS"]
        if (item := _build_tagged_item(bullet, result_table, chunk_lookup)) is not None
    ]
    if not facts:
        return {"insights": _fallback_report(result_table, result.plan_summary), "status": "in_progress"}

    insights = InsightReport(
        facts=facts,
        recommendations=recommendations,
        trends=_validated_bullets(sections["TRENDS"], result_table),
        anomalies=_validated_bullets(sections["ANOMALIES"], result_table),
    )
    return {"insights": insights, "status": "in_progress"}
