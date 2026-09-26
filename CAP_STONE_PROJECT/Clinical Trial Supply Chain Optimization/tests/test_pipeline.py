"""Unit + integration tests — a subset of CLAUDE.md §17's required scenarios."""
import pytest

from app.orchestrator import decide_approval, run_assessment

SCOPE = ["PH3-ONC-2027"]


def test_low_risk_site_completes_without_approval():
    r = run_assessment("IND001", SCOPE)
    assert r.risk_level == "LOW"
    assert r.final_status == "COMPLETED"
    assert r.approval_required is False
    assert len(r.evidence_ids) == 3
    assert r.latency_ms is not None and r.latency_ms >= 0


def test_high_risk_site_requires_approval():
    r = run_assessment("IND002", SCOPE)
    assert r.risk_level == "HIGH"
    assert r.approval_required is True
    assert r.final_status == "PENDING_APPROVAL"


def test_critical_site_no_incoming_shipment():
    r = run_assessment("IND003", SCOPE)
    assert r.risk_level == "CRITICAL"
    assert r.approval_required is True
    assert r.days_to_stockout <= 7


def test_missing_enrollment_data_is_insufficient_evidence():
    r = run_assessment("IND004", SCOPE)
    assert r.final_status == "INSUFFICIENT_EVIDENCE"
    assert r.risk_level is None


def test_stale_inventory_forces_approval_even_if_low_risk():
    r = run_assessment("IND005", SCOPE)
    assert r.approval_required is True
    stale_check = next(c for c in r.guardrail_results if c.check == "EVIDENCE_COMPLETENESS")
    assert stale_check.status == "WARN"
    assert r.confidence_score < 0.9


def test_unauthorized_site_is_blocked_before_any_agent_runs():
    r = run_assessment("IND201", SCOPE)
    assert r.final_status == "BLOCKED_UNAUTHORIZED"
    assert r.risk_level is None
    assert r.evidence_ids == []


def test_approval_gate_accepts_authorized_role():
    r = run_assessment("IND002", SCOPE)
    approved = decide_approval(r.request_id, "Clinical Supply Manager", "APPROVED", None)
    assert approved.final_status == "APPROVED"
    assert approved.approval.approver_role == "Clinical Supply Manager"
    assert approved.approval.decision == "APPROVED"


def test_approval_gate_rejects_unauthorized_role_rbac():
    r = run_assessment("IND002", SCOPE)
    with pytest.raises(PermissionError):
        decide_approval(r.request_id, "Logistics Coordinator", "APPROVED", None)


def test_rejection_requires_a_reason():
    r = run_assessment("IND003", SCOPE)
    with pytest.raises(ValueError):
        decide_approval(r.request_id, "Global Trial Supply Planner", "REJECTED", None)


def test_rejection_with_reason_returns_workflow_for_revision():
    r = run_assessment("IND003", SCOPE)
    rejected = decide_approval(r.request_id, "Global Trial Supply Planner", "REJECTED", "awaiting updated count")
    assert rejected.final_status == "REJECTED"
    assert rejected.approval.reason == "awaiting updated count"


def test_duplicate_request_ids_are_unique_per_run():
    r1 = run_assessment("IND001", SCOPE)
    r2 = run_assessment("IND001", SCOPE)
    assert r1.request_id != r2.request_id
