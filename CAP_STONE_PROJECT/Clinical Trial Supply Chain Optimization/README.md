# Supply Pulse — Clinical Trial Stockout Risk Assessment Agent

A prototype built against [`CLAUDE.md`](./CLAUDE.md). It answers one question on
demand: *which clinical trial sites are at risk of investigational-product
stockout within 30 days, why, and what should a supply manager review?*

All data is synthetic. This is decision support only — it never releases,
cancels, or authorizes a shipment.

## What's here

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Governing specification — scope, boundaries, phases, Definition of Done |
| `app/models.py` | Pydantic models for sites, reports, guardrail results, approval decisions |
| `app/fixtures.py` | 6 synthetic sites, including 3 built to trip a specific guardrail |
| `app/agents.py` | Demand, Inventory, Risk, and Compliance agents (deterministic, no LLM) |
| `app/mcp_mock.py` | Mock read-only MCP layer — tool allowlist, scope enforcement, source/timestamp/schema-version envelopes |
| `app/orchestrator.py` | Validates scope, reads through the mock MCP layer, runs the pipeline, enforces fail-closed guardrails |
| `app/db.py` | SQLite persistence for run state, the audit trail, the MCP call log, and the Q&A log |
| `app/main.py` | FastAPI app — `/`, `/sites`, `/assess`, `/approve`, `/audit`, `/mcp-log`, `/tests`, `/ask`, `/qa-log` |
| `app/static/index.html` | Dashboard UI — site picker, live assessment, approval, audit trail, MCP call log, test results, Ask panel |
| `app/qa.py` | Read-only conversational Q&A layer — the only place an LLM is called |
| `tests/test_pipeline.py` | pytest suite covering the core positive/negative scenarios |
| `tests/test_mcp_mock.py` | pytest suite covering the MCP allowlist, scope enforcement, and envelope shape |
| `ip_runway_prototype.html` | Standalone documentation + simulated walkthrough of the full CLAUDE.md scope (architecture, MCP, governance, evaluation) — a presentation layer, not this backend |

## Run it

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8842
```

Open **http://127.0.0.1:8842/** for the dashboard (site picker, live assessment, approve/reject, audit trail, and a "Run tests" panel). The raw Swagger UI is still available at `/docs` for direct API calls:

```bash
curl -s -X POST http://127.0.0.1:8842/assess -H "Content-Type: application/json" \
  -d '{"site_id": "IND002", "requesting_scope": ["PH3-ONC-2027"]}'
```

Run the tests from the command line:

```bash
pytest tests/ -v
```

or hit `GET /tests` (also wired to the dashboard's "Run tests" button) — it shells out to the real suite on every call, so the numbers are live, not cached.

## Testing & test scenario results

CLAUDE.md §17 lists 12 required test scenarios. This prototype's `tests/test_pipeline.py` and `tests/test_mcp_mock.py` cover 8 of them directly (2 partially), with 17 total pytest cases (some scenarios need more than one test):

| # | Scenario (§17) | Covered by |
|---|---|---|
| 1 | Normal LOW-risk site | `test_low_risk_site_completes_without_approval` |
| 2 | HIGH-risk site requiring approval | `test_high_risk_site_requires_approval` |
| 3 | CRITICAL site, possible patient impact | `test_critical_site_no_incoming_shipment` |
| 4 | Missing enrollment or inventory data | `test_missing_enrollment_data_is_insufficient_evidence` (enrollment only) |
| 5 | Conflicting MCP sources | ⚠️ partially covered — `test_mcp_mock.py` proves the allowlist/scope/provenance contract, but the mock has one fixture source per site, so there's no second, conflicting source to reconcile |
| 6 | Stale or malformed tool response | `test_stale_inventory_forces_approval_even_if_low_risk` (stale only) |
| 7 | Unauthorized study/site request | `test_unauthorized_site_is_blocked_before_any_agent_runs` |
| 8 | Prompt injection inside a document | ❌ not covered — no document ingestion exists |
| 9 | Attempted ERP or shipment modification | ❌ not covered — no write path exists to attempt this against |
| 10 | MCP timeout, agent exception, memory-resume | ⚠️ partially covered — `test_unknown_tool_is_rejected_by_the_allowlist` / `test_unknown_site_raises_not_found` cover agent-side exception handling; there's no network transport to time out since the mock is synchronous and in-process |
| 11 | Approval, rejection, missing-approval paths | `test_approval_gate_accepts_authorized_role`, `test_approval_gate_rejects_unauthorized_role_rbac`, `test_rejection_requires_a_reason`, `test_rejection_with_reason_returns_workflow_for_revision` |
| 12 | Duplicate request / idempotent replay | `test_duplicate_request_ids_are_unique_per_run` (uniqueness only, not replay) |

**Live result at last run: 18/18 passed.** Run `GET /tests` or click "Run tests" on the dashboard to reproduce this yourself — it is not a fixed number pasted into this file.

## The mock MCP layer

`app/mcp_mock.py` is the single choke point every agent read goes through — `app/agents.py`'s functions no longer import fixtures at all, and `app/orchestrator.py` calls `get_site_master` / `get_enrollment` / `get_inventory` / `get_shipment` instead of touching `SITES` directly. This is the concrete, code-level version of CLAUDE.md §12's "Pre-tool: allowlist MCP tools and enforce read-only access":

- **Allowlist**: `call_tool` rejects anything not in `ALLOWED_TOOLS` (the four read tools above) with `MCPToolNotAllowed`, before it ever looks at a site.
- **Scope enforcement**: enrollment/inventory/shipment reads check the requesting scope against the site's study independently of the orchestrator's own check — `MCPUnauthorized` fires even if called directly, not just through `/assess`. Site-master (study/country/status/protocol constants) is treated as non-sensitive directory data, so it's readable pre-authorization — that's how the orchestrator learns a site's study ID in the first place.
- **Envelopes**: every response carries `source_id`, `retrieved_at`, `schema_version`, and `authorization_context`, per §13.
- **Logging**: every call is written to the `mcp_calls` table and exposed at `GET /mcp-log` (and the dashboard's "MCP tool calls" panel) — the audit trail for exactly which reads happened, in what order, under what scope.

It is still not a real MCP transport — no client/server protocol, no stdio/HTTP boundary — which is exactly what §13 permits for the MVP: "local mock MCP servers backed by synthetic fixtures; clearly label them as mocks." This labels it as one.

## Sample data

| site_id | Demonstrates |
|---|---|
| IND001 | LOW risk, completes without approval |
| IND002 | HIGH risk, routes to `/approve` |
| IND003 | CRITICAL risk, no incoming shipment |
| IND004 | missing enrollment data → `INSUFFICIENT_EVIDENCE` |
| IND005 | stale inventory data → forces approval regardless of risk |
| IND201 | outside authorized study scope → blocked before any agent runs |

## The conversational layer

`app/qa.py` calls an LLM (`anthropic/claude-haiku-4.5` via OpenRouter) — the only place in the prototype that does. It is deliberately boxed in:

- It can only read `AssessmentReport` rows already persisted by the deterministic pipeline (`list_runs` in `app/db.py`) — it never re-runs an agent, calls a tool, or sees anything the pipeline didn't already compute.
- It cannot approve, reject, or trigger any action — read-only, matching CLAUDE.md §7 and §15.
- If asked about a site with no persisted run, it says so instead of guessing.
- Every answer is cross-checked in code for site IDs (`IND\d+`) that appear in the answer but not in the source records, and flagged as unverified if so — a lightweight, automated groundedness check rather than a manual one.
- Every question, answer, and the request IDs it was grounded on are logged to `qa_log` (`GET /qa-log`) for traceability.

Try it from the dashboard's "Ask" panel, e.g. *"Which sites are at risk of stockout in the next 30 days, and why?"* — or directly:

```bash
curl -s -X POST http://127.0.0.1:8842/ask -H "Content-Type: application/json" \
  -d '{"question": "Which sites are at risk of stockout in the next 30 days, and why?"}'
```

## Governance and observability capture (§10, §12, §16, §21)

Every pipeline run and every LLM call now records the fields CLAUDE.md's governance and observability sections require, not just a pass/fail result:

- **Latency**: `AssessmentReport.latency_ms` is the whole Orchestrator→...→Compliance pipeline duration (measured with `time.perf_counter()` in `app/orchestrator.py`), set on all three outcomes — `BLOCKED_UNAUTHORIZED`, `INSUFFICIENT_EVIDENCE`, and the full-completion path. Each mock MCP call is timed independently in `app/mcp_mock.py` and stored in `mcp_calls.latency_ms`, visible at `GET /mcp-log`.
- **Model/prompt governance**: `app/qa.py` records `model` (`anthropic/claude-haiku-4.5`) and `prompt_version` (`qa-v1`) on every Q&A call, plus OpenRouter's `prompt_tokens`/`completion_tokens` usage and the LLM call's own latency — all persisted in `qa_log` (`GET /qa-log`) and returned directly in the `/ask` response body, not just logged.
- **Approval record**: `decide_approval` in `app/orchestrator.py` used to validate `approver_role`/`decision`/`reason` and then discard them, leaving only `final_status` — a real gap against §16 ("Record approver role, decision, reason, timestamp, and recommendation version"). It now builds an `ApprovalRecord` (`app/models.py`) with all four and persists it on `AssessmentReport.approval`, surfaced in `/approve`'s response and the dashboard's "Decision recorded" panel.
- The dashboard's audit-trail and MCP-call tables show a Latency column; the Ask panel shows model/prompt-version/token/latency under each answer.

## Known gaps against CLAUDE.md

This is a short prototype, not the full spec. Not implemented:

- **MCP transport**: `app/mcp_mock.py` implements the allowlist/scope/envelope/logging contract of §13 in-process (see "The mock MCP layer" above), but there is no actual client/server protocol or network boundary — §13 explicitly permits this for the MVP.
- **Full shared state object**: SQLite persists the final report per run, not the complete `plan` / `agent_outputs` / `current_step` workflow object in §14, and there's no resume-from-last-state.
- **Named skills**: the 6 skills in §11 exist as plain functions inside the agents, not as independently declared, tested units.
- **LLM scope**: the risk calculations themselves are still deterministic Python (by design — CLAUDE.md §15 requires separating deterministic calc from LLM narrative). The LLM is used only in the Ask layer described above, not for risk logic.
- **Evaluation harness (§18)**: the pytest suite proves behavioral correctness (18/18 passing), not the groundedness/calibration/actionability rubric.
