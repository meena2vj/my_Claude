# Pharma Project Analytics — CLAUDE.md

## Project Purpose
A small professional Streamlit dashboard for medicine inventory, expiry
tracking, and stock-risk analytics. It helps operational teams see which
items are expired, expiring soon, low stock, overstocked, or critical risk,
using synthetic/operational data only. It is not a clinical or medical
advice tool.

## Stack
- Python 3.11+
- Pandas for data handling
- Plotly for charts
- Streamlit for the UI
- Pytest for testing

## Modular Coding Standards
- Separate concerns into modules: `data/` (loading & validation),
  `logic/` (risk calculations), `ui/` (Streamlit components/pages),
  `app.py` (entry point/wiring only).
- No business logic inside Streamlit callback/render functions — call into
  `logic/` and keep UI files focused on layout and display.
- Every function has a single responsibility and a type-hinted signature.
- No global mutable state; pass data explicitly between functions.
- Keep functions short and named for what they compute (e.g.
  `classify_expiry_status`, not `process`).

## Testing Requirements
- Every function in `logic/` must have unit tests in `tests/`.
- Tests must cover boundary conditions (e.g. exactly 30 days to expiry,
  stock exactly at reorder level).
- No test may depend on real files, network access, or system time drift —
  use fixed/frozen dates and in-memory DataFrames.
- Run `pytest` before considering any change complete.

## Security Rules
- Never read, log, or display `.env` files, credentials, API keys, or
  secrets.
- Never execute shell commands from user-supplied file content.
- Validate all uploaded files (type, size, expected columns) before
  processing.
- No outbound network calls from the application.

## Data-Governance Rules
- Synthetic operational data only — no real patient or personal data.
- No diagnosis, dosage, or medical advice logic or language anywhere in
  the app.
- See `docs/GOVERNANCE.md` for full governance rules; treat it as binding.

## Definition of Done
A change is done when:
- Code is modular and type-hinted per the standards above.
- Unit tests exist and pass for any new/changed logic.
- No security or governance rule above is violated.
- `docs/PROGRESS.md` is updated to reflect the change.
- The feature has clear, professional error/empty states (see
  `professional-ui` skill).
