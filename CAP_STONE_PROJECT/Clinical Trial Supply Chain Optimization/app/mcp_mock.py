"""Mock read-only MCP layer — CLAUDE.md §13.

A real MCP server speaks a client/server protocol over a transport (stdio,
HTTP). This mock does not implement that transport, but it keeps the same
contract: every response carries a source ID, retrieval timestamp, schema
version, and authorization context, and it is the single choke point every
agent must pass through to reach fixture data. That makes the pre-tool
allowlist and scope check below real enforcement (§12), not decoration —
an agent cannot bypass it by importing SITES directly, because agents no
longer import SITES at all (see app/agents.py, app/orchestrator.py).
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from app.db import log_mcp_call
from app.fixtures import SITES

SCHEMA_VERSION = "1.0"

# Site master (study/country/status/protocol constants) is non-sensitive
# directory data, so it is readable without a scope match — an authorized
# scope is still required for every other tool.
ALLOWED_TOOLS = {"get_site_master", "get_enrollment", "get_inventory", "get_shipment"}
SCOPED_TOOLS = {"get_enrollment", "get_inventory", "get_shipment"}


class MCPToolNotAllowed(Exception):
    pass


class MCPUnauthorized(Exception):
    pass


class MCPSiteNotFound(Exception):
    pass


def _envelope(tool: str, site_id: str, data: dict, requesting_scope: list[str], latency_ms: float) -> dict:
    envelope = {
        "data": data,
        "source_id": f"mock-mcp:{tool}:{site_id}",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": SCHEMA_VERSION,
        "authorization_context": list(requesting_scope),
    }
    log_mcp_call(tool, site_id, envelope["source_id"], list(requesting_scope), latency_ms)
    return envelope


def call_tool(tool: str, site_id: str, requesting_scope: list[str]) -> dict:
    """Single entry point for every read. Allowlists the tool, then enforces scope."""
    start = time.perf_counter()

    if tool not in ALLOWED_TOOLS:
        raise MCPToolNotAllowed(f"'{tool}' is not an allow-listed MCP tool.")

    site = SITES.get(site_id)
    if site is None:
        raise MCPSiteNotFound(site_id)

    if tool in SCOPED_TOOLS and site.study_id not in requesting_scope and site.site_id not in requesting_scope:
        raise MCPUnauthorized(f"{site_id} (study {site.study_id}) is outside scope {requesting_scope}.")

    if tool == "get_site_master":
        data = {
            "site_id": site.site_id,
            "study_id": site.study_id,
            "country": site.country,
            "status": site.status,
            "kit_per_visit": site.kit_per_visit,
            "visit_interval_days": site.visit_interval_days,
        }
    elif tool == "get_enrollment":
        data = site.enrollment.model_dump(mode="json")
    elif tool == "get_inventory":
        data = site.inventory.model_dump(mode="json")
    else:  # get_shipment
        data = site.shipment.model_dump(mode="json")

    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    return _envelope(tool, site_id, data, requesting_scope, latency_ms)


def get_site_master(site_id: str, requesting_scope: list[str]) -> dict:
    return call_tool("get_site_master", site_id, requesting_scope)


def get_enrollment(site_id: str, requesting_scope: list[str]) -> dict:
    return call_tool("get_enrollment", site_id, requesting_scope)


def get_inventory(site_id: str, requesting_scope: list[str]) -> dict:
    return call_tool("get_inventory", site_id, requesting_scope)


def get_shipment(site_id: str, requesting_scope: list[str]) -> dict:
    return call_tool("get_shipment", site_id, requesting_scope)
