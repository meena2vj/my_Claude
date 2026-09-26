"""FastAPI app — CLAUDE.md §8. Run: uvicorn app.main:app --reload --port 8842

Interactive docs (Swagger UI) at /docs double as the local test console.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.db import list_mcp_calls, list_qa, list_runs
from app.fixtures import SITES
from app.mcp_mock import MCPSiteNotFound, get_site_master
from app.models import ApprovalDecision, AskRequest, AssessRequest, AssessmentReport
from app.orchestrator import SiteNotFound, decide_approval, run_assessment
from app.qa import QAUnavailable, answer_question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Supply Pulse — Clinical Trial Stockout Risk Assessment Agent",
    description="Agentic AI prototype built against CLAUDE.md. Synthetic data only.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# CLAUDE.md §17 required test scenarios mapped to the actual pytest tests that cover them.
SCENARIO_MAP = {
    "test_low_risk_site_completes_without_approval": "1. Normal LOW-risk site",
    "test_high_risk_site_requires_approval": "2. HIGH-risk site requiring approval",
    "test_critical_site_no_incoming_shipment": "3. CRITICAL site, possible patient impact",
    "test_missing_enrollment_data_is_insufficient_evidence": "4. Missing enrollment data",
    "test_stale_inventory_forces_approval_even_if_low_risk": "6. Stale tool response",
    "test_unauthorized_site_is_blocked_before_any_agent_runs": "7. Unauthorized study/site request",
    "test_approval_gate_accepts_authorized_role": "11. Approval path",
    "test_approval_gate_rejects_unauthorized_role_rbac": "11. Approval path (RBAC block)",
    "test_rejection_requires_a_reason": "11. Rejection path (missing reason)",
    "test_rejection_with_reason_returns_workflow_for_revision": "11. Rejection path (with reason)",
    "test_duplicate_request_ids_are_unique_per_run": "12. Duplicate request",
    "test_unknown_tool_is_rejected_by_the_allowlist": "5/10. MCP pre-tool allowlist (mock)",
    "test_scoped_tool_rejects_out_of_scope_request": "5/10. MCP scope enforcement (mock)",
    "test_site_master_is_readable_without_scope": "5/10. MCP directory-data read (mock)",
    "test_unknown_site_raises_not_found": "5/10. MCP unknown-site handling (mock)",
    "test_envelope_carries_required_provenance_fields": "5/10. MCP envelope provenance (mock)",
}
SCENARIOS_NOT_COVERED = [
    "5. Conflicting MCP sources — mock MCP has one fixture source per site, so there is nothing to conflict; a real MCP integration would need this",
    "8. Prompt injection inside a document — no document ingestion implemented",
    "9. Attempted ERP or shipment modification — no write path exists to attempt this against",
    "10. MCP timeout / agent exception / memory-resume — mock MCP is synchronous and in-process, so there is no network timeout to simulate; allowlist/scope/not-found failure modes are covered",
]


@app.get("/", tags=["meta"], include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", tags=["meta"])
def api_info():
    return {
        "name": "Supply Pulse",
        "docs": "/docs",
        "sites": "/sites",
        "assess": "POST /assess",
        "approve": "POST /approve",
        "audit": "/audit",
        "tests": "/tests",
        "mcp_log": "/mcp-log",
    }


@app.get("/sites", tags=["fixtures"])
def get_sites():
    """List the synthetic sites available to assess, with a hint of what each demonstrates."""
    hints = {
        "IND001": "LOW risk — healthy stock",
        "IND002": "HIGH risk — requires approval",
        "IND003": "CRITICAL risk — no incoming shipment",
        "IND004": "guardrail test — missing enrollment data",
        "IND005": "guardrail test — stale inventory data",
        "IND201": "guardrail test — outside authorized study scope",
    }
    return [
        {"site_id": s.site_id, "study_id": s.study_id, "country": s.country, "hint": hints.get(s.site_id, "")}
        for s in SITES.values()
    ]


@app.get("/sites/{site_id}", tags=["fixtures"])
def get_site(site_id: str):
    """Site-master directory data only — enrollment/inventory/shipment require
    a scoped /assess call through the mock MCP layer, not this endpoint."""
    try:
        return get_site_master(site_id, requesting_scope=[])
    except MCPSiteNotFound:
        raise HTTPException(404, f"Unknown site {site_id}")


@app.post("/assess", response_model=AssessmentReport, tags=["pipeline"])
def assess(req: AssessRequest):
    """Run the Orchestrator -> Demand -> Inventory -> Risk -> Compliance pipeline for one site.

    Sample body:
    {"site_id": "IND002", "requesting_scope": ["PH3-ONC-2027"]}
    """
    try:
        return run_assessment(req.site_id, req.requesting_scope)
    except SiteNotFound:
        raise HTTPException(404, f"Unknown site {req.site_id}")


@app.post("/approve", response_model=AssessmentReport, tags=["pipeline"])
def approve(decision: ApprovalDecision):
    """Record a human approval/rejection for a PENDING_APPROVAL request.

    Sample body:
    {"request_id": "REQ-XXXXXXXX", "approver_role": "Clinical Supply Manager", "decision": "APPROVED"}
    """
    try:
        return decide_approval(decision.request_id, decision.approver_role, decision.decision, decision.reason)
    except SiteNotFound:
        raise HTTPException(404, f"Unknown request {decision.request_id}")
    except PermissionError as exc:
        raise HTTPException(403, str(exc))
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/audit", tags=["observability"])
def audit(limit: int = 50):
    """Session audit trail — CLAUDE.md §20-21 traceability output."""
    return list_runs(limit)


@app.post("/ask", tags=["conversational"])
def ask(req: AskRequest):
    """Read-only Q&A over already-persisted assessments — CLAUDE.md §2.2 / §15.

    This is the only endpoint that calls an LLM, and the LLM here can only
    narrate audit-trail records that the deterministic pipeline already
    computed. It cannot run an assessment, approve/reject, or touch a site
    that has no prior record.
    """
    try:
        return answer_question(req.question)
    except QAUnavailable as exc:
        raise HTTPException(503, str(exc))


@app.get("/qa-log", tags=["conversational"])
def qa_log(limit: int = 20):
    """History of questions asked and the run IDs each answer was grounded on."""
    return list_qa(limit)


@app.get("/mcp-log", tags=["observability"])
def mcp_log(limit: int = 20):
    """Every mock-MCP tool call — tool, site, source ID, requesting scope, timestamp.

    This is the pre-tool allowlist + scope-check hook (§12) made observable
    (§20-21): every enrollment/inventory/shipment/site-master read the agents
    made is here, in call order, whether or not the request was ultimately
    authorized.
    """
    return list_mcp_calls(limit)


@app.get("/tests", tags=["observability"])
def run_tests():
    """Live pytest run against CLAUDE.md §17's required scenarios — not a fabricated score.

    Shells out to the real test suite on every call, so the numbers reflect the
    code as it stands right now, not a cached or illustrative benchmark.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=no", "--no-header"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    results = []
    for line in proc.stdout.splitlines():
        m = re.match(r"^\S+::(\w+)\s+(PASSED|FAILED)", line)
        if m:
            name, outcome = m.groups()
            results.append(
                {"test": name, "outcome": outcome, "scenario": SCENARIO_MAP.get(name, "unmapped")}
            )
    passed = sum(1 for r in results if r["outcome"] == "PASSED")
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
        "scenarios_not_covered": SCENARIOS_NOT_COVERED,
    }
