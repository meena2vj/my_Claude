---
name: professional-ui
description: UI/UX standards for the Pharma Project Analytics Streamlit dashboard (theme, layout, KPIs, charts, states).
---

# Professional UI Standards

Apply these standards to every Streamlit page/component in this project.

## Theme & Layout
- Light corporate theme: white/light-grey background, one accent colour
  for primary actions, neutral greys for text and borders.
- Responsive layout using Streamlit columns/containers; avoid fixed pixel
  widths that break on narrower screens.
- A moving header line reading "Project Analytics" (e.g. a subtle
  marquee/animated text strip) appears at the top of the app, once.
- No excessive animations elsewhere — the header line is the only
  intentional motion; everything else is static and calm.

## KPI Cards
- Use clear KPI cards (metric + label) for top-level numbers: total
  items, expired count, expiring-soon count, low-stock count,
  critical-risk count.
- Keep KPI cards visually consistent (same size, spacing, and colour
  language across the row).

## Colour Consistency
- Use one fixed colour per risk category everywhere it appears (KPI
  cards, tables, charts, badges): e.g. red = EXPIRED/CRITICAL RISK,
  orange = EXPIRING SOON/LOW STOCK, blue/purple = OVERSTOCK, green = SAFE.
- Never reuse a risk colour for an unrelated meaning.

## Accessible Charts
- All Plotly charts must have axis labels, a legend when more than one
  series, and sufficient colour contrast (avoid red/green-only
  distinctions without labels or patterns).
- Add hover text with plain-language values, not raw codes.

## Filters
- Keep filters clean and minimal: category, risk status, date range.
- Filters live in a sidebar or a single filter row — not scattered
  across the page.

## Error & Empty States
- No uploaded file yet: show a calm, professional prompt explaining what
  to upload and the expected columns — never a raw stack trace.
- Invalid file: show a specific, actionable error message (what's wrong,
  what's expected).
- No rows matching current filters: show a clear "no results" message,
  not a blank page or broken chart.
