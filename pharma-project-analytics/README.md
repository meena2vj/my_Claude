# Pharma Project Analytics

A professional Streamlit dashboard for medicine inventory, expiry
tracking, and stock-risk analytics. It helps operational teams see which
batches are expired, expiring soon, low stock, overstocked, or critical
risk — using synthetic/operational data only. **This is not a clinical
or medical advice tool.**

## Features

- Upload your own CSV/Excel inventory file, or explore the bundled
  synthetic sample dataset out of the box.
- Sidebar filters (medicine, category, warehouse, expiry status, stock
  status, risk level) with a one-click reset.
- KPI cards, five Plotly charts, and five tabs: Executive Dashboard, Risk
  Analysis, Data Quality, Data Preview, Governance.
- Downloadable Processed Inventory, Critical-Risk, and Data-Quality
  reports.
- Deterministic, transparent risk rules — no ML or LLM anywhere in the
  app (see `.claude/skills/pharma-risk/SKILL.md` and
  `docs/DATA_DICTIONARY.md`).

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Python 3.11+ is expected. No API keys, database, or login are required —
see `.env.example` (a placeholder only; nothing in it is mandatory).

## Uploading your own data

Expected columns (see `docs/DATA_DICTIONARY.md` for details):

```
Batch_ID, Medicine_Name, Category, Manufacturer, Manufacturing_Date,
Expiry_Date, Current_Stock, Reorder_Level, Maximum_Stock, Unit_Price,
Warehouse, Critical_Medicine
```

Uploaded files are validated (type, size, required columns) and
processed **in memory for the current session only** — nothing you
upload is written to disk or sent anywhere else.

## Governance

All data must be synthetic or de-identified operational sample data —
see `docs/GOVERNANCE.md` for the full, binding rules (no PII, no
diagnosis/dosage/medical-advice content, calculation transparency,
session-only processing, human review of Critical-Risk results, and more).
The in-app Governance tab surfaces the same notices at runtime.

## Testing

```bash
pytest
```

Every function in `src/` (data loading, upload validation, parsing, data
quality, risk engine, analytics, report generation, filters) has unit
tests covering documented boundary conditions. UI rendering code in
`src/ui/` and `app.py` is verified by running the app directly, per
`CLAUDE.md`.

## Project structure

```
app.py                entry point — wiring only
src/data_loader.py     disk CSV loading + validation (bundled sample)
src/upload.py           in-memory CSV/Excel upload validation + parsing
src/parsing.py           shared safe-parsing helpers
src/data_quality.py      missing/duplicate/invalid-date/negative-stock checks
src/risk_engine.py       expiry/stock/risk classification rules
src/analytics.py         aggregations over risk-engine output
src/report_generator.py  summary/markdown report generation
src/filters.py           sidebar filter logic
src/ui_theme.py          shared colours/styling constants
src/ui/                  Streamlit rendering components (header, sidebar,
                         KPI cards, charts, tabs, states)
docs/                    governance, progress log, data dictionary
.claude/                 hooks, skills, and the pharma-auditor subagent
```
