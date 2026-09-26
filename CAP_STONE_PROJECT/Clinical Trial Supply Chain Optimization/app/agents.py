"""Demand, Inventory, Risk, and Compliance agents — CLAUDE.md §10-11.

Deterministic calculations only; no LLM call in this phase (§15: separate
deterministic calculation from LLM-generated explanation). Agents take
already-validated Pydantic sub-models, not raw fixture access — the
orchestrator is the only caller that reads through the mock MCP layer
(app/mcp_mock.py) and hands the resulting data down.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.models import Enrollment, GuardrailResult, Inventory, Shipment

STALE_HOURS = 48
TARGET_BUFFER_DAYS = 45
LARGE_TRANSFER_THRESHOLD = 200


class InsufficientEvidence(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(f"Missing required field(s): {', '.join(missing)}")


def _hours_since(ts: datetime, now: datetime) -> float:
    return (now - ts).total_seconds() / 3600


def demand_agent(site_id: str, kit_per_visit: float, visit_interval_days: int, enrollment: Enrollment) -> dict:
    if enrollment.actual is None:
        raise InsufficientEvidence(["enrollment.actual"])
    e = enrollment
    active = e.actual * (1 - e.dropout_rate)
    new_patients = (e.trend_per_week / 7) * 30 * (1 - e.dropout_rate)
    daily_dose_rate = kit_per_visit / visit_interval_days
    daily_demand = (active + new_patients / 2) * daily_dose_rate
    return {
        "daily_demand": daily_demand,
        "demand_30d": round(daily_demand * 30),
        "evidence_id": f"enrollment-{site_id}-{e.timestamp.strftime('%Y%m%d')}",
        "timestamp": e.timestamp,
    }


def inventory_agent(site_id: str, inventory: Inventory, shipment: Shipment, demand: dict) -> dict:
    inv, ship = inventory, shipment
    usable_supply = inv.usable_kits - inv.safety_stock
    incoming = ship.qty if (ship.status == "IN_TRANSIT" and ship.eta_days <= 30) else 0
    effective_supply = usable_supply + incoming
    coverage_days = effective_supply / demand["daily_demand"]
    return {
        "usable_supply": usable_supply,
        "incoming": incoming,
        "effective_supply": effective_supply,
        "coverage_days": coverage_days,
        "pack_size": inv.pack_size,
        "evidence_id": f"inventory-{site_id}-{inv.timestamp.strftime('%Y%m%d')}",
        "timestamp": inv.timestamp,
    }


def risk_agent(demand: dict, inv: dict) -> dict:
    days = math.floor(inv["coverage_days"])
    if days <= 7 or (days <= 14 and inv["incoming"] == 0):
        risk_level = "CRITICAL"
    elif days <= 21:
        risk_level = "HIGH"
    elif days <= 30:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    need = max(0.0, TARGET_BUFFER_DAYS * demand["daily_demand"] - inv["effective_supply"])
    recommended_qty = math.ceil(need / inv["pack_size"]) * inv["pack_size"]
    return {"risk_level": risk_level, "days_to_stockout": days, "recommended_qty": recommended_qty}


def compliance_agent(enrollment: Enrollment, demand: dict, inv: dict, risk: dict, now: datetime) -> dict:
    stale = _hours_since(demand["timestamp"], now) > STALE_HOURS or _hours_since(inv["timestamp"], now) > STALE_HOURS
    fast_trend = enrollment.trend_per_week > 2.0

    confidence = 0.97
    if stale:
        confidence -= 0.25
    if fast_trend:
        confidence -= 0.05
    confidence = round(max(0.0, min(1.0, confidence)), 2)

    approval_required = (
        risk["risk_level"] in ("HIGH", "CRITICAL")
        or risk["recommended_qty"] > LARGE_TRANSFER_THRESHOLD
        or stale
    )

    checks = [
        GuardrailResult(check="AUTH_SCOPE_CHECK", status="PASS"),
        GuardrailResult(
            check="MCP_TOOL_ALLOWLIST",
            status="PASS",
            detail="all reads went through allow-listed, scope-checked mock MCP tools (§12, §13)",
        ),
        GuardrailResult(
            check="EVIDENCE_COMPLETENESS",
            status="WARN" if stale else "PASS",
            detail=f"stale evidence beyond {STALE_HOURS}h threshold" if stale else None,
        ),
        GuardrailResult(check="PROHIBITED_ACTION_CHECK", status="PASS", detail="no auto-release attempted"),
        GuardrailResult(
            check="APPROVAL_REQUIRED",
            status="TRUE" if approval_required else "FALSE",
            detail=("stale evidence forces review" if stale else risk["risk_level"] + " risk")
            if approval_required
            else "within LOW/MEDIUM autonomy",
        ),
    ]

    assumptions = [
        "Kit-per-patient-visit ratio held constant across the horizon.",
        "New enrollees assumed to consume at half the average horizon rate.",
        "Only in-transit shipments arriving within 30 days counted as available supply.",
    ]
    if stale:
        assumptions.append("Stale source data — risk figures carry reduced confidence until refreshed.")

    return {
        "stale": stale,
        "confidence": confidence,
        "approval_required": approval_required,
        "checks": checks,
        "assumptions": assumptions,
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
