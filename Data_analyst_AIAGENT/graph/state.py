"""Shared LangGraph state schema for the Data Analyst AI Agent.

`AgentState` is a TypedDict (what LangGraph expects) whose structured fields
are pydantic models rather than bare dicts, so every node reads/writes a
validated shape instead of an untyped blob.
"""

from typing import Literal, TypedDict

import pandas as pd
from pydantic import BaseModel, Field


class KPIDefinition(BaseModel):
    name: str
    definition: str
    target: str | None = None
    direction: Literal["increase", "decrease", "maintain"] = "increase"


class RawDataMeta(BaseModel):
    filename: str
    upload_ts: str
    rows: int
    columns: int
    dtypes: dict[str, str]


class ColumnIssue(BaseModel):
    column: str
    count: int
    percentage: float


class QualityReport(BaseModel):
    row_count: int
    column_count: int
    missing_by_column: list[ColumnIssue]
    duplicate_row_count: int
    duplicate_row_percentage: float
    outliers_by_column: list[ColumnIssue]
    numeric_columns: list[str]
    categorical_columns: list[str]
    unique_counts: dict[str, int]
    invalid_value_columns: list[ColumnIssue]
    constant_columns: list[str]
    descriptive_stats: dict[str, dict[str, float]]


class CleaningAction(BaseModel):
    action_id: str
    action_type: str
    column: str | None = None
    description: str
    destructive: bool
    rows_before: int
    rows_after: int
    executed: bool = False


class BusinessContextDoc(BaseModel):
    doc_id: str
    filename: str
    upload_ts: str


class ContextChunk(BaseModel):
    chunk_id: str
    doc_id: str
    filename: str
    page: int
    text: str
    token_count: int


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    ts: str


class AnalysisResult(BaseModel):
    kpi_matched: str | None = None
    plan_summary: str
    result_table_json: str
    narrative: str
    validated: bool = False
    validation_notes: list[str] = Field(default_factory=list)


class ChartSpec(BaseModel):
    chart_type: str
    plotly_json: str
    question: str
    title: str


class CitationRef(BaseModel):
    filename: str
    page: int
    snippet: str


class InsightItem(BaseModel):
    text: str
    tag: Literal["data-derived", "cited"]
    citation: CitationRef | None = None


class InsightReport(BaseModel):
    facts: list[InsightItem]
    recommendations: list[InsightItem]
    trends: list[str] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)


class EmailDraft(BaseModel):
    subject: str
    body: str
    editable: bool = True


class AgentError(BaseModel):
    node: str
    message: str
    severity: Literal["warning", "fatal"]
    ts: str


class AgentState(TypedDict):
    session_id: str
    trace_id: str

    problem_statement: str
    kpis: list[KPIDefinition]

    raw_data: pd.DataFrame | None
    raw_data_meta: RawDataMeta | None

    quality_report: QualityReport | None

    cleaning_plan: list[CleaningAction]
    cleaning_log: list[CleaningAction]
    clean_data: pd.DataFrame | None
    cleaning_confirmed: bool

    business_context_docs: list[BusinessContextDoc]
    business_context_chunks: list[ContextChunk]
    business_context_index_ready: bool

    user_question: str
    conversation_history: list[ChatTurn]
    analysis_result: AnalysisResult | None
    charts: list[ChartSpec]

    insights: InsightReport | None

    report_path: str | None
    email_draft: EmailDraft | None

    errors: list[AgentError]
    retry_count: dict[str, int]
    status: Literal["in_progress", "awaiting_user", "error", "complete"]


def new_state(session_id: str, trace_id: str) -> AgentState:
    """Build a fresh AgentState with empty/default values."""
    return AgentState(
        session_id=session_id,
        trace_id=trace_id,
        problem_statement="",
        kpis=[],
        raw_data=None,
        raw_data_meta=None,
        quality_report=None,
        cleaning_plan=[],
        cleaning_log=[],
        clean_data=None,
        cleaning_confirmed=False,
        business_context_docs=[],
        business_context_chunks=[],
        business_context_index_ready=False,
        user_question="",
        conversation_history=[],
        analysis_result=None,
        charts=[],
        insights=None,
        report_path=None,
        email_draft=None,
        errors=[],
        retry_count={},
        status="in_progress",
    )
