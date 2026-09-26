"""Pydantic models — CLAUDE.md §4 output schema and §14 shared state."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
FinalStatus = Literal[
    "COMPLETED",
    "PENDING_APPROVAL",
    "APPROVED",
    "REJECTED",
    "INSUFFICIENT_EVIDENCE",
    "BLOCKED_UNAUTHORIZED",
]


class Enrollment(BaseModel):
    actual: int | None
    dropout_rate: float
    trend_per_week: float
    timestamp: datetime


class Inventory(BaseModel):
    usable_kits: int
    safety_stock: int
    pack_size: int
    timestamp: datetime


class Shipment(BaseModel):
    status: Literal["IN_TRANSIT", "PLANNED", "DELAYED"]
    eta_days: int
    qty: int


class Site(BaseModel):
    site_id: str
    study_id: str
    country: str
    status: str
    enrollment: Enrollment
    inventory: Inventory
    shipment: Shipment
    kit_per_visit: float
    visit_interval_days: int


class AssessRequest(BaseModel):
    site_id: str
    requesting_scope: list[str]


class GuardrailResult(BaseModel):
    check: str
    status: Literal["PASS", "WARN", "FAIL", "TRUE", "FALSE"]
    detail: str | None = None


class ApprovalRecord(BaseModel):
    approver_role: str
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = None
    decided_at: datetime


class AssessmentReport(BaseModel):
    request_id: str
    site_id: str
    study_id: str | None = None
    risk_level: RiskLevel | None = None
    days_to_stockout: int | None = None
    demand_30d: int | None = None
    recommended_action: str | None = None
    confidence_score: float | None = None
    approval_required: bool = False
    evidence_ids: list[str] = []
    assumptions: list[str] = []
    guardrail_results: list[GuardrailResult] = []
    final_status: FinalStatus
    generated_at: datetime
    latency_ms: float | None = None
    approval: ApprovalRecord | None = None


class AskRequest(BaseModel):
    question: str


class ApprovalDecision(BaseModel):
    request_id: str
    approver_role: Literal[
        "Clinical Supply Manager",
        "Global Trial Supply Planner",
        "Logistics Coordinator",
    ]
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = None
