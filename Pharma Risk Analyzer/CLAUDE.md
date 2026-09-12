CLAUDE: Mini Pharma Shipment Risk Analyzer — Design & Components

This document (CLAUDE.md) describes a minimal architecture called "Claude" for a small Streamlit-based Pharma Shipment Risk Analyzer. It lists the required components (skills, subagents, and hooks), assumptions, heuristics, and extension ideas.

Goal
Provide a tiny web app that accepts an Excel shipment dataset and highlights high-risk shipments and temperature excursions, with a brief AI-style recommendation.

User story
As a logistics/QA user I can upload a shipment Excel file and immediately see: total shipments, number of high-risk shipments, temperature-excursion shipments, the top-5 highest-risk shipments, a risk distribution chart, and short recommendations.

Components (high-level)
- Skill: `file_parser` — robustly read Excel (multiple sheets), normalize columns to lowercase, detect candidate ID/temperature/delay columns.
- Skill: `risk_engine` — compute a deterministic risk score per shipment using simple heuristics (temperature excursions, delays, missing critical data).
- Skill: `viz` — render tables and charts (Altair/Streamlit) for distribution and top-risk items.
- Skill: `recommendation` — generate short, template-based AI-style recommendations from metrics.

Subagents (conceptual)
- `Explore` — quick dataset inspection: sample rows, inferred schema, column suggestions.
- `Score` — apply `risk_engine` to each row and produce risk bands.
- `Summarize` — aggregate metrics and synthesize concise recommendations.

Hooks and integration points
- `on_upload` hook: triggered when a user uploads a file — calls `file_parser` then `Explore`.
- `on_analyze` hook: calls `Score` then `Summarize` and `viz` to render outputs.

Heuristics & Risk Scoring (mini-proposal)
- Default safe temperature range: 2°C–8°C (configurable).
- Score weights (example):
  - Temperature excursion detected: +60
  - temp_min/temp_max outside safe range: +40
  - Delay > 24 hours: +20, >6h: +10
  - Missing critical fields (shipment_id, temperature): +10 each
- Risk band: high-risk if score >= 60.

Assumptions about input dataset
- Column names may vary; we normalize to lowercase and try common alternatives:
  - shipment_id (aliases: `id`, `tracking_id`, `tracking`)
  - temperature (`temperature`, `temp`)
  - temp_min / temp_max
  - delay_hours or timestamp/delivery_timestamp to derive delays (not implemented in mini)

Files in this mini-project
- `app.py` — Streamlit UI + file uploader and orchestration.
- `analysis.py` — parsing, risk scoring, metrics, recommendation generator.
- `requirements.txt` — dependencies.
- `README.md` — run instructions.

Extensibility ideas
- Add an LLM-backed recommendation subagent for richer narratives.
- Plug connectors to monitoring systems (S3, object stores) and add automated alerts.
- Add carrier scoring and trend analysis.

Safety & privacy
Avoid uploading real PHI/PII to third-party services. This mini-app processes files locally in the user's Streamlit session.

End of CLAUDE.md
