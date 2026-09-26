"""Orchestrator — CLAUDE.md §10. Validates scope, runs the agent pipeline,
enforces the pre-request guardrail, and fails closed on missing evidence.

Every site/enrollment/inventory/shipment read goes through app/mcp_mock.py
rather than touching fixtures directly — that module is the pre-tool
allowlist + scope-check hook required by §12, and every call it makes is
logged for §20/§21 traceability (see GET /mcp-log).
"""
from __future__ import annotations

import time
import uuid

from app.agents import (
    InsufficientEvidence,
    compliance_agent,
    demand_agent,
    inventory_agent,
    risk_agent,
    utcnow,
)
from app.db import save_run
from app.mcp_mock import MCPSiteNotFound, get_enrollment, get_inventory, get_shipment, get_site_master
from app.models import ApprovalRecord, AssessmentReport, Enrollment, GuardrailResult, Inventory, Shipment


class SiteNotFound(Exception):
    pass


def run_assessment(site_id: str, requesting_scope: list[str]) -> AssessmentReport:
    request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    now = utcnow()
    start = time.perf_counter()

    try:
        site_master = get_site_master(site_id, requesting_scope)
    except MCPSiteNotFound:
        raise SiteNotFound(site_id)

    master = site_master["data"]
    study_id = master["study_id"]

    # Pre-request guardrail — fail closed on unauthorized scope (§7, §15).
    if study_id not in requesting_scope and site_id not in requesting_scope:
        report = AssessmentReport(
            request_id=request_id,
            site_id=site_id,
            final_status="BLOCKED_UNAUTHORIZED",
            guardrail_results=[
                GuardrailResult(
                    check="AUTH_SCOPE_CHECK",
                    status="FAIL",
                    detail=f"Site {site_id} (study {study_id}) is outside the requesting user's authorized scope.",
                )
            ],
            generated_at=now,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        save_run(request_id, site_id, report.final_status, report.model_dump(mode="json"))
        return report

    enrollment_env = get_enrollment(site_id, requesting_scope)
    enrollment = Enrollment.model_validate(enrollment_env["data"])

    try:
        demand = demand_agent(site_id, master["kit_per_visit"], master["visit_interval_days"], enrollment)
    except InsufficientEvidence as exc:
        report = AssessmentReport(
            request_id=request_id,
            site_id=site_id,
            study_id=study_id,
            final_status="INSUFFICIENT_EVIDENCE",
            guardrail_results=[
                GuardrailResult(check="EVIDENCE_COMPLETENESS", status="FAIL", detail=str(exc))
            ],
            generated_at=now,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        save_run(request_id, site_id, report.final_status, report.model_dump(mode="json"))
        return report

    inventory_env = get_inventory(site_id, requesting_scope)
    shipment_env = get_shipment(site_id, requesting_scope)
    inventory = Inventory.model_validate(inventory_env["data"])
    shipment = Shipment.model_validate(shipment_env["data"])

    inv = inventory_agent(site_id, inventory, shipment, demand)
    risk = risk_agent(demand, inv)
    compliance = compliance_agent(enrollment, demand, inv, risk, now)

    final_status = "PENDING_APPROVAL" if compliance["approval_required"] else "COMPLETED"

    report = AssessmentReport(
        request_id=request_id,
        site_id=site_id,
        study_id=study_id,
        risk_level=risk["risk_level"],
        days_to_stockout=risk["days_to_stockout"],
        demand_30d=demand["demand_30d"],
        recommended_action=f"Review shipment of {risk['recommended_qty']} kits",
        confidence_score=compliance["confidence"],
        approval_required=compliance["approval_required"],
        evidence_ids=[demand["evidence_id"], inv["evidence_id"], f"shipment-{site_id}"],
        assumptions=compliance["assumptions"],
        guardrail_results=compliance["checks"],
        final_status=final_status,
        generated_at=now,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )
    save_run(request_id, site_id, report.final_status, report.model_dump(mode="json"))
    return report


def decide_approval(request_id: str, approver_role: str, decision: str, reason: str | None) -> AssessmentReport:
    from app.db import get_run

    stored = get_run(request_id)
    if stored is None:
        raise SiteNotFound(request_id)

    report = AssessmentReport.model_validate(stored)
    if report.final_status != "PENDING_APPROVAL":
        raise ValueError(f"Request {request_id} is not pending approval (status={report.final_status}).")

    if approver_role == "Logistics Coordinator":
        raise PermissionError("Logistics Coordinator cannot approve HIGH/CRITICAL recommendations (RBAC).")
    if decision == "REJECTED" and not reason:
        raise ValueError("A reason is required to reject.")

    report.final_status = "APPROVED" if decision == "APPROVED" else "REJECTED"
    report.approval = ApprovalRecord(
        approver_role=approver_role,
        decision=report.final_status,
        reason=reason,
        decided_at=utcnow(),
    )
    save_run(request_id, report.site_id, report.final_status, report.model_dump(mode="json"))
    return report
