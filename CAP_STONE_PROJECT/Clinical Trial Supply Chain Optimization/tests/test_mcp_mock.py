"""Mock MCP layer tests — CLAUDE.md §12 pre-tool hook and §13 MCP integration.

These test the mock MCP module directly, independent of the orchestrator, to
prove the allowlist and scope check are real enforcement rather than something
only exercised by the one call path run_assessment happens to take.
"""
import pytest

from app.mcp_mock import (
    ALLOWED_TOOLS,
    MCPSiteNotFound,
    MCPToolNotAllowed,
    MCPUnauthorized,
    call_tool,
    get_enrollment,
    get_site_master,
)
from app.db import list_mcp_calls

SCOPE = ["PH3-ONC-2027"]


def test_unknown_tool_is_rejected_by_the_allowlist():
    with pytest.raises(MCPToolNotAllowed):
        call_tool("delete_shipment", "IND001", SCOPE)


def test_allowed_tools_reject_nothing_by_name():
    assert ALLOWED_TOOLS == {"get_site_master", "get_enrollment", "get_inventory", "get_shipment"}


def test_scoped_tool_rejects_out_of_scope_request():
    with pytest.raises(MCPUnauthorized):
        get_enrollment("IND001", requesting_scope=["PH2-CARD-2026"])


def test_site_master_is_readable_without_scope():
    envelope = get_site_master("IND001", requesting_scope=[])
    assert envelope["data"]["study_id"] == "PH3-ONC-2027"


def test_unknown_site_raises_not_found():
    with pytest.raises(MCPSiteNotFound):
        get_site_master("IND999", requesting_scope=[])


def test_envelope_carries_required_provenance_fields():
    envelope = get_enrollment("IND001", SCOPE)
    assert envelope["source_id"] == "mock-mcp:get_enrollment:IND001"
    assert envelope["schema_version"] == "1.0"
    assert envelope["authorization_context"] == SCOPE
    assert "retrieved_at" in envelope


def test_logged_call_records_a_non_negative_latency():
    get_enrollment("IND001", SCOPE)
    latest = list_mcp_calls(limit=1)[0]
    assert latest["latency_ms"] >= 0
