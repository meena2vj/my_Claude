"""Node: answer the user's question over `clean_data`.

Numbers only ever come from `tools/analysis_ops.py` executing Pandas on
`clean_data`. The LLM (if configured) only picks which KPI/grouping to
narrate -- `validate_narrative_against_result` checks every number the LLM
states against the actual result table, and a mismatch forces a retry
(capped by `MAX_ANALYST_RETRIES`, see `graph/conditions.py::route_on_validation`)
rather than reaching the user.
"""

from graph.state import AgentState, AnalysisResult, ChatTurn, KPIDefinition
from config.settings import INSUFFICIENT_CONTEXT_MESSAGE, SHORT_TERM_MEMORY_TURNS
from observability.metrics import record_tool_call
from observability import trace_store
from services import memory_service
from services.llm_client import call_llm
from tools.analysis_ops import aggregate_by_group, match_column, validate_narrative_against_result
from datetime import datetime, timezone
import hashlib

_SYSTEM_PROMPT = (
    "You are a data analyst. You are given NUMERIC_DATA -- the exact, "
    "already-computed result table for the user's question -- and, "
    "optionally, BUSINESS_CONTEXT excerpts and CONVERSATION_HISTORY. Write a "
    "short (2-4 sentence) plain-English explanation of NUMERIC_DATA. Every "
    "number you state MUST appear in NUMERIC_DATA verbatim -- never invent or "
    "round differently. Use BUSINESS_CONTEXT only for qualitative framing, "
    "and CONVERSATION_HISTORY only to resolve references and follow-ups "
    "(e.g. \"that region\", \"vs last time\") -- neither is ever a source of "
    "numbers."
)


def _plan_columns(
    question: str, numeric_cols: list[str], categorical_cols: list[str], kpis: list[KPIDefinition]
) -> tuple[str | None, str | None]:
    value_col = None
    for kpi in kpis:
        value_col = match_column(kpi.name, numeric_cols) or match_column(kpi.definition, numeric_cols)
        if value_col:
            break
    if value_col is None:
        for word in question.split():
            value_col = match_column(word, numeric_cols)
            if value_col:
                break
    if value_col is None and numeric_cols:
        value_col = numeric_cols[0]

    group_col = None
    for word in question.split():
        group_col = match_column(word, categorical_cols)
        if group_col:
            break
    if group_col is None and categorical_cols:
        group_col = categorical_cols[0]

    return value_col, group_col


def _dataset_fingerprint(df) -> str:
    raw = f"{sorted(df.columns)}|{len(df)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


def _format_conversation_history(history: list[ChatTurn]) -> str:
    recent = history[-SHORT_TERM_MEMORY_TURNS:]
    if not recent:
        return "(no prior turns this session)"
    return "\n".join(f"{turn.role.upper()}: {turn.content}" for turn in recent)


def run(state: AgentState) -> dict:
    if state["clean_data"] is None or not state["user_question"].strip():
        return {"status": "awaiting_user"}

    df = state["clean_data"]
    question = state["user_question"]
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = [c for c in df.columns if c not in numeric_cols]
    value_col, group_col = _plan_columns(question, numeric_cols, categorical_cols, state["kpis"])

    if value_col is None:
        return {
            "analysis_result": AnalysisResult(
                plan_summary="No numeric column available to analyze.",
                result_table_json="[]",
                narrative=INSUFFICIENT_CONTEXT_MESSAGE,
                validated=True,
            ),
            "status": "in_progress",
        }

    try:
        result_table = aggregate_by_group(df, value_col, group_col)
    except Exception:
        record_tool_call("aggregate_by_group", ok=False)
        raise
    record_tool_call("aggregate_by_group", ok=True)
    trace_store.log_event(
        trace_id=state["trace_id"], node="analyst", event_type="tool_call", status="ok",
        tool_name="aggregate_by_group", input_summary=f"value={value_col} group={group_col}",
        output_summary=f"{len(result_table)} rows",
    )
    plan_summary = f"Aggregated '{value_col}' by '{group_col}'." if group_col else f"Summarized '{value_col}'."

    numeric_block = result_table.to_string(index=False)
    context_block = (
        "\n\n".join(f"[{c.filename} p.{c.page}] {c.text}" for c in state["business_context_chunks"][:5])
        or "(no business context documents uploaded)"
    )
    history_block = _format_conversation_history(state["conversation_history"])
    user_prompt = (
        f"QUESTION: {question}\n\nNUMERIC_DATA:\n{numeric_block}\n\n"
        f"BUSINESS_CONTEXT (qualitative, cite only):\n{context_block}\n\n"
        f"CONVERSATION_HISTORY (context/follow-ups only, cite no numbers from here):\n{history_block}"
    )

    llm_result = call_llm(_SYSTEM_PROMPT, user_prompt, node_name="analyst", trace_id=state["trace_id"])
    narrative = llm_result.text if llm_result.ok else f"{plan_summary} See the result table for the exact figures."

    validation_notes = validate_narrative_against_result(narrative, result_table)
    validated = not validation_notes

    retry_count = dict(state["retry_count"])
    if not validated:
        retry_count["analyst"] = retry_count.get("analyst", 0) + 1

    update: dict = {
        "analysis_result": AnalysisResult(
            kpi_matched=value_col,
            plan_summary=plan_summary,
            result_table_json=result_table.to_json(orient="records"),
            narrative=narrative,
            validated=validated,
            validation_notes=validation_notes,
        ),
        "retry_count": retry_count,
        "status": "in_progress",
    }
    if validated:
        now = datetime.now(timezone.utc).isoformat()
        update["conversation_history"] = [
            *state["conversation_history"],
            ChatTurn(role="user", content=question, ts=now),
            ChatTurn(role="assistant", content=narrative, ts=now),
        ]
        fingerprint = _dataset_fingerprint(df)
        kpi_context = ", ".join(k.name for k in state["kpis"]) or None
        memory_service.save_turn(
            session_id=state["session_id"], trace_id=state["trace_id"], role="user",
            content=question, kpi_context=kpi_context, dataset_fingerprint=fingerprint,
        )
        memory_service.save_turn(
            session_id=state["session_id"], trace_id=state["trace_id"], role="assistant",
            content=narrative, kpi_context=kpi_context, dataset_fingerprint=fingerprint,
        )
    return update
