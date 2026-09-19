---
name: analyst-ui
description: UI/UX standards for the Data Analyst AI Agent Streamlit app (theme, layout, KPIs, charts, states). Shared reference for the main agent and the data-analyst-auditor.
---

# Analyst UI Standards

Apply these standards to every `ui/tab_*.py` file and to `ui/sidebar.py`.

## Theme & Layout
- Light corporate theme defined in `ui/theme.py`: background `#F8FAFC`,
  surface `#FFFFFF`, ink text `#0F172A`, muted text `#64748B`, border
  `#E2E8F0`, primary accent `#2563EB`. Reuse these constants — never
  hardcode a different palette in a tab file.
- One animated element only: the top ticker headline rendered once by
  `theme.render_headline()` ("DATA ANALYST AI AGENT — From Raw Data to
  Decision Intelligence"). Everything else in the UI is static and calm.
- Layout via `st.columns`/`st.tabs`/`st.expander` — avoid fixed pixel
  widths that break at narrower browser widths.

## KPI Cards
- Use `theme.kpi_card(label, value)` for every top-level metric tile
  (row counts, error counts, latency, success rate, etc.) so cards stay
  visually consistent across tabs (Data Quality, Observability,
  Dashboard).
- Keep a KPI row to 3-5 cards; if there are more values to show, put the
  rest in a table below the row rather than growing the row indefinitely.

## Colour Consistency
- Reuse `theme.SUCCESS` (`#16A34A`), `theme.WARNING` (`#D97706`), and
  `theme.DANGER` (`#DC2626`) for the same meaning everywhere: success =
  green, needs-attention/destructive-pending = amber, error = red. Never
  reuse one of these for an unrelated meaning in a different tab.

## Accessible Charts
- Every Plotly chart from `tools/chart_builders.py` must have axis
  labels and a title (`ChartSpec.title`); add a legend whenever more than
  one series/group is plotted.
- Prefer hover text with plain-language values over raw column codes.

## Filters & Inputs
- Keep each tab's inputs minimal and scoped to that tab's stage of the
  workflow (e.g. Data Upload only asks for a file; Ask Your Data only
  asks a question) — don't collect inputs for a later stage early.
- Session/resume controls (session ID display, "Resume a prior session")
  live in `ui/sidebar.py` only, not duplicated per tab.

## Error & Empty States
- A tab whose prerequisite state field is `None`/empty (no file
  uploaded, no quality report yet, no question asked) must show a calm
  `st.info`/`st.warning` prompt explaining what's missing and which
  earlier tab to complete — never a raw traceback or a blank page.
- A destructive cleaning action pending confirmation must be shown
  clearly (amber, with an explicit confirm button) before
  `cleaning_confirmed` can become `True` — never auto-confirmed by the UI.
- Validation failures (e.g. a narrative that failed
  `validate_narrative_against_result`) must surface as a clear retry/error
  message, not a silently-substituted answer.
