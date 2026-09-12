# Progress Log — Pharma Project Analytics

## Phase 1 — Project Setup and Claude Code Configuration
Status: Complete

Deliverables:
- [x] CLAUDE.md (project purpose, stack, modular standards, testing,
  security, data-governance rules, definition of done)
- [x] docs/GOVERNANCE.md (synthetic data only, no PII, no medical advice,
  data minimisation, file validation, calculation transparency, data
  lineage, session-only processing, human review of critical risk,
  limitations)
- [x] docs/PROGRESS.md (this file)
- [x] .claude/hooks/safety_check.py — PreToolUse hook blocking destructive
  deletion commands, access to `.env`/secret files, credential-exposure
  commands, and file/command paths outside the project directory
- [x] .claude/hooks/quality_check.py — PostToolUse hook that runs a fast
  `py_compile` syntax check on modified `.py` files (no long-running
  processes)
- [x] .claude/settings.json — wires both hooks (PreToolUse matches all
  tools; PostToolUse matches Write|Edit)
- [x] .claude/skills/pharma-risk/SKILL.md — expiry/stock/critical-risk
  classification rules
- [x] .claude/skills/professional-ui/SKILL.md — theme, layout, KPI,
  colour, chart, filter, and error/empty-state standards
- [x] .claude/agents/pharma-auditor.md — read-only auditor subagent
  (Read/Grep/Glob only)
- [x] Validation of hooks/skills/subagent with safe simulated inputs

### Validation notes
- `safety_check.py` was tested with 10 simulated PreToolUse payloads:
  safe Bash commands and in-project file reads were allowed; `rm -rf /`,
  `git push --force`, `cat .env`, `echo $API_KEY`, `printenv`, an Edit
  targeting `.env`, and a Read of `/etc/passwd` were all blocked (exit
  code 2). One bug was found and fixed during validation: the
  credential-exposure regexes for `echo $VAR` and `export VAR=...`
  originally expected uppercase variable names but were matched against
  a lower-cased command string, so they never matched — patterns were
  corrected to lowercase.
- `quality_check.py` was tested with a valid `.py` file (exit 0), a
  `.py` file with a syntax error (exit 2, error reported), a non-Python
  file (skipped, exit 0), and a missing file path (no crash, exit 0).
- `.claude/settings.json` validated as well-formed JSON with `jq`, and
  both hook entries resolve to the expected commands.
- SKILL.md and agent frontmatter for `pharma-risk`, `professional-ui`,
  and `pharma-auditor` all parse correctly.

No application code has been built in this phase, per instructions.

## Phase 1 Verification
Status: Complete — 2 configuration errors found and fixed in `safety_check.py`

Re-checked CLAUDE.md, docs/GOVERNANCE.md, both hooks, `.claude/settings.json`,
both SKILL.md files, and the pharma-auditor agent against the original Phase 1
requirements. Re-ran simulated PreToolUse/PostToolUse payloads (safe inputs
only — no destructive commands were executed).

### Errors found and fixed
1. **`cd /tmp` was wrongly blocked.** The generic path-token scan exempted
   `/tmp` and `/dev/null`, but a separate, redundant `cd`-specific regex check
   did not carry the same exemption, so `cd /tmp && ls` was denied.
2. **Quoted absolute paths bypassed the "outside project directory" check
   entirely.** The path-token regex only recognised a path when it was
   preceded by whitespace, so `cat "/etc/passwd"` was allowed (exit 0) while
   the unquoted `cat /etc/passwd` was correctly blocked — a real
   security-relevant false negative. The same whitespace-splitting also
   truncated in-project paths, since this project's own root directory name
   contains a space ("Finance analytics"), causing legitimate quoted
   in-project references to be misread as outside the project.

**Fix:** replaced the naive whitespace/regex tokenizer in
`check_bash_command()` with `shlex.split()`, which handles quoting correctly
(preserves spaces inside quoted arguments, recognises quoted paths as paths).
The separate, redundant `cd`-specific regex block was removed and replaced
with a token-based check using the same tokens and the same `/tmp`/`/dev/null`
exemption as the general path scan.

### Re-validation after fix
- All 10 original simulated test cases (safe Bash, `rm -rf`, `git push
  --force`, `cat .env`, `echo $API_KEY`, `printenv`, Edit on `.env`, Read of
  `/etc/passwd`, in-project Read, unrelated tool) still produce the expected
  allow/block results.
- New cases added and verified: `cd /tmp` now allowed; `cd /` still blocked;
  quoted `cat "/etc/passwd"` now blocked; quoted in-project paths (including
  paths under this project's space-containing root) now correctly allowed;
  quoted `cd` to a path outside the project now blocked.
- `quality_check.py` re-tested (valid `.py`, syntax-error `.py`, non-Python
  file, missing file) — all four still behave as expected; no changes needed.
- `.claude/settings.json` re-validated with `jq` — both hook entries resolve
  correctly; no changes needed.
- Both hook scripts re-compiled cleanly with `py_compile` after the fix.
- Frontmatter for both SKILL.md files and the pharma-auditor agent re-parsed
  correctly (name, description, and `tools` fields all present and valid);
  no changes needed.
- CLAUDE.md and docs/GOVERNANCE.md content re-checked against the original
  required outline — intact, no errors found, no changes needed.

No changes were made outside `.claude/hooks/safety_check.py`. No application
code was built or modified.

## Phase 2 — Dataset, Data Quality, and Risk Engine
Status: Complete

Deliverables:
- [x] `scripts/generate_dataset.py` — deterministic (fixed seed, fixed
  anchor date) generator for the synthetic dataset
- [x] `data/pharma_inventory.csv` — 200 synthetic medicine batch records
  (195 unique + 5 exact duplicate rows), with controlled counts of every
  required edge case: 20 expired batches, 20 expiring within 30 days, 20
  low stock, 20 overstock, 15 rows with a missing value, 10 rows with
  invalid/malformed dates, 10 rows with negative stock, 5 duplicate
  pairs
- [x] `src/data_loader.py` — file validation (extension, size, required
  columns) and CSV loading; rejects invalid files with a clear
  `DataValidationError` rather than guessing/repairing; drops any
  non-required columns (data minimisation)
- [x] `src/parsing.py` — shared safe-parsing helpers (`to_float`,
  `to_date`, `to_yes_no`, `is_blank`) used by both `data_quality.py` and
  `risk_engine.py`; every helper returns `None` for blank/invalid input
  instead of raising or guessing
- [x] `src/data_quality.py` — deterministic checks for the four required
  data-quality dimensions (missing values, duplicate records, invalid
  dates, negative stock), returned as a `DataQualityReport`; detects and
  reports only, never mutates the input
- [x] `src/risk_engine.py` — deterministic Python rules producing
  `Days_To_Expiry`, `Expiry_Status`, `Stock_Status`, `Inventory_Value`,
  `Risk_Score`, `Risk_Level` (Critical/High/Medium/Low), and
  `Recommended_Action`. Expiry Status, Stock Status, and the Critical
  Risk combination rule match `.claude/skills/pharma-risk/SKILL.md`
  exactly, including boundary conditions. Risk_Score/Risk_Level/
  Recommended_Action are a documented Phase 2 extension on top of that
  skill (an additive point system with fixed thresholds — no ML/LLM).
  Missing/invalid inputs produce explicit `UNKNOWN`/`INVALID` outcomes
  rather than a guessed value.
- [x] `src/analytics.py` — deterministic pandas aggregations over the
  risk-engine output (risk-level counts, inventory value by category/at
  risk, expiring-soon/low-stock/overstock subsets, critical-medicine and
  per-warehouse summaries)
- [x] `src/report_generator.py` — deterministic dict/markdown summary
  reports combining `analytics` output and an optional
  `DataQualityReport`; Critical-risk items are listed for human review
  only, never acted on automatically
- [x] `docs/DATA_DICTIONARY.md` — documents every source and derived
  column, the exact Risk_Score point table and Risk_Level thresholds,
  and the four data-quality dimensions with their controlled dataset
  counts
- [x] `tests/test_data_quality.py`, `tests/test_risk_engine.py` — the
  two test files required by the task, covering every function in both
  modules and the boundary conditions named in `CLAUDE.md` (exactly 30
  days to expiry, stock exactly at reorder level, stock exactly at
  maximum stock, risk-level threshold edges)
- [x] `tests/test_data_loader.py`, `tests/test_parsing.py`,
  `tests/test_analytics.py`, `tests/test_report_generator.py` — added
  after the audit (see below) so every function in `src/` has coverage,
  per `CLAUDE.md`'s blanket testing requirement
- [x] `conftest.py` — empty file at the project root so pytest resolves
  `from src... import` correctly; no test behaviour depends on it
  otherwise

All tests use fixed/frozen reference dates and in-memory DataFrames —
none depend on real files, network access, or system time drift.
`pytest` run: **148 passed, 0 failed**.

### Audit (general-purpose agent, following `.claude/agents/pharma-auditor.md`'s
criteria)
Note: the `pharma-auditor` custom subagent type defined in
`.claude/agents/pharma-auditor.md` is not registered as an invocable
agent type in this environment (only built-in agent types are
available here). A `general-purpose` agent was used instead, explicitly
instructed to follow the pharma-auditor's exact persona, six review
categories, and read-only constraint (no edits).

Findings: **no blockers**. Three should-fix items, all implemented:
1. No tests existed for `src/data_loader.py` (file-validation logic
   underpinning the governance "File Validation" rule) — fixed by
   adding `tests/test_data_loader.py` (extension rejection, size-limit
   rejection, missing-file rejection, missing-column rejection,
   malformed-CSV rejection, extra-column dropping).
2. No tests existed for `src/parsing.py`, `src/analytics.py`, or
   `src/report_generator.py` — fixed by adding
   `tests/test_parsing.py`, `tests/test_analytics.py`, and
   `tests/test_report_generator.py`.
3. `docs/PROGRESS.md` had not been updated for Phase 2 — fixed by this
   entry.

Confirmed clean by the audit (no changes needed): data-quality logic,
risk-calculation accuracy and boundary conditions, security (no shell
execution, no secrets/PII access, no network calls), governance
compliance (no PII fields, no diagnosis/dosage/medical-advice language,
no silent repair of bad data, Critical Risk only ever flagged for human
review). Streamlit interface quality (category 6) was reported "not
applicable" — no UI is built in this phase.

No Streamlit dashboard or `app.py`/`ui/` was built in this phase, per
instructions.

## Phase 2 Verification
Status: Complete — 1 confirmed data-quality gap found and fixed

Re-validated Phase 2 against 10 named boundary cases by exercising the
running code directly (not just trusting the existing unit tests), using
`.claude/skills/pharma-risk/SKILL.md` as the source of truth for
Expiry/Stock Status.

### Boundary cases checked

| Case | Result | Outcome |
|---|---|---|
| Already expired | `Days_To_Expiry = -1` → `EXPIRED` | Correct |
| Expiring today | `Days_To_Expiry = 0` → `EXPIRING_SOON` | Correct |
| Expiring in exactly 30 days | `Days_To_Expiry = 30` → `EXPIRING_SOON` | Correct |
| Expiring after 30 days | `Days_To_Expiry = 31` → `SAFE` | Correct |
| Zero stock | `Current_Stock = 0` (below any positive reorder level) → `LOW_STOCK` | Correct |
| Stock equal to reorder level | `Current_Stock == Reorder_Level` → `NORMAL` (strict inequality) | Correct |
| Stock above maximum level | `Current_Stock > Maximum_Stock` → `OVERSTOCK` | Correct |
| Missing expiry date | Blank `Expiry_Date` → `Days_To_Expiry` missing, `Expiry_Status = UNKNOWN` | Correct |
| Negative stock | `Current_Stock < 0` → `Stock_Status = INVALID`, `Inventory_Value` missing | Correct |
| Duplicate Batch_ID | Two rows sharing a `Batch_ID` with **different** other-column data | **Bug found** — see below |

9 of 10 cases were already correct with no code changes needed. New
tests were added to make three of these boundary cases explicit at the
integration (`apply_risk_engine`) or unit level where they were
previously only implied: `test_zero_stock_is_low_stock` and
`test_missing_expiry_date_is_unknown` in `tests/test_risk_engine.py`.

### Bug found and fixed: duplicate Batch_ID with conflicting data

`check_duplicate_rows()` only flags rows that are identical across
**every** column. Two rows sharing the same `Batch_ID` but disagreeing
on other fields (e.g. same ID, different `Current_Stock`/`Warehouse`) —
a worse integrity problem, since `Batch_ID` is meant to be a unique key
and it becomes ambiguous which row is authoritative — passed through
undetected. Confirmed directly:

```python
row1 = {"Batch_ID": "BATCH-9999", ..., "Current_Stock": 100, "Warehouse": "WH-North"}
row2 = dict(row1, Current_Stock=999, Warehouse="WH-South")
check_duplicate_rows(pd.DataFrame([row1, row2]))  # -> [] (bug)
```

**Fix:**
- Added `check_duplicate_batch_ids()` to `src/data_quality.py` — flags
  every non-blank `Batch_ID` that appears on more than one row,
  regardless of whether the other columns agree. This necessarily also
  catches every exact full-row duplicate (since those share a
  `Batch_ID` too), so it is a strict superset of the conflicting-data
  case that `check_duplicate_rows` misses.
- Added `duplicate_batch_id_groups` to `DataQualityReport`, wired into
  `has_issues()`, `summary()`, and `run_data_quality_checks()`.
- Added a "Duplicate Batch_IDs" line to `report_generator.generate_markdown_report()`.
- Added `TestCheckDuplicateBatchIds` (5 cases: unique IDs not flagged,
  same ID with conflicting data flagged, exact duplicate row also
  flagged, blank Batch_ID excluded, three-way same-ID group) and a new
  aggregate-level test (`test_duplicate_batch_id_with_conflicting_data_is_detected`)
  to `tests/test_data_quality.py`; updated
  `test_report_aggregates_all_dimensions` to assert on the new field and
  summary keys.
- Documented the new dimension in `docs/DATA_DICTIONARY.md`'s "Data
  Quality Dimensions" table, distinct from "Duplicate records", with an
  explanation of why the two checks are kept separate.

Detection only — per `docs/GOVERNANCE.md`, no row is dropped or
auto-repaired; conflicting duplicates are reported for human review.

### Test suite

`pytest` run: **156 passed, 0 failed** (up from 148; +8 tests: 5 for
`check_duplicate_batch_ids`, 1 aggregate-level duplicate-Batch_ID test,
1 for zero stock, 1 for missing expiry date at the integration level).

No other files were changed. No Streamlit dashboard was built.

## Phase 3 — Professional Streamlit Dashboard
Status: Complete

Deliverables:
- [x] `app.py` — entry point/wiring only: page config, header render,
  uploader, sample/upload load-and-enrich pipeline (with
  `DataValidationError`/generic-exception handling and a fallback to the
  bundled sample on a bad upload), filters, and tab dispatch
- [x] `src/upload.py` — in-memory CSV/Excel upload validation and parsing
  (extension, size, required columns); never writes to disk; any parse
  failure (malformed CSV, or an Excel file `openpyxl` cannot open) is
  wrapped in a clear `DataValidationError` rather than propagating
- [x] `src/filters.py` — pure, testable `FilterSelection` dataclass and
  `apply_filters()` (AND logic across Medicine/Category/Warehouse/
  Expiry-status/Stock-status/Risk-level; empty list = no restriction)
- [x] `src/ui_theme.py` — single source of truth for the light corporate
  palette and the fixed risk/expiry/stock colour maps, reused by every
  KPI card, chart, and table
- [x] `src/ui/header.py` — title, subtitle, and the CSS marquee (light
  blue background, dark navy text, smooth right-to-left scroll,
  hover-pause, `prefers-reduced-motion` support) containing the required
  "Project Analytics" text
- [x] `src/ui/sidebar.py` — CSV/Excel uploader (`render_uploader`) and the
  six filter multiselects plus Reset Filters (`render_filters`), split
  into two functions to resolve the circular dependency between "filter
  options depend on the resolved dataset" and "the uploader must render
  before the dataset is resolved"
- [x] `src/ui/kpi.py` — the six KPI cards (Total Batches, Total Inventory
  Value, Expired Batches, Expiring Soon, Low-Stock Batches, Critical-Risk
  Batches), coloured by risk-based accent
- [x] `src/ui/charts.py` — the five Plotly charts (Batches by Risk Level,
  Inventory Value by Category, Expiry Timeline, Low Stock by Warehouse,
  Top Critical Medicine Batches), each with axis labels, legends where
  relevant, plain-language hover text, and a calm empty-state figure
  when there is no data to show
- [x] `src/ui/tabs.py` — Executive Dashboard, Risk Analysis, Data Quality,
  Data Preview, and Governance tabs, including the three download
  buttons (Processed Inventory, Critical-Risk, Data-Quality reports) and
  the governance disclosures (synthetic data, no medical advice,
  calculation rules, data-quality issues, session-only processing)
- [x] `src/ui/states.py` — loading, empty-data, invalid-file, success, and
  generic-error state renderers
- [x] `.streamlit/config.toml`, `requirements.txt`, `.env.example`,
  updated `.gitignore`, `README.md`
- [x] `tests/test_upload.py`, `tests/test_filters.py` — full coverage of
  the two new business-logic modules, using in-memory `io.BytesIO`
  fixtures only (no real files/network)

No LLM, database, or authentication was added, per instructions.

`pytest` run: **173 passed, 0 failed** (up from 156).

Manual verification: the app was run headless (`streamlit run app.py
--server.headless true`), confirmed healthy via `/_stcore/health`, and
screenshotted with headless Chrome. Confirmed rendering: title/subtitle/
marquee, the bundled-sample lineage caption, all five tab labels, all six
KPI cards with correct values and risk-based colours, the first two
charts with correct colours/legends/axis labels, the full sidebar
(uploader + six filters + Reset Filters), and a working download button.

### Audit (general-purpose agent, following `.claude/agents/pharma-auditor.md`'s
criteria)
As in Phase 2, the custom `pharma-auditor` subagent type is not invocable
directly in this environment; a `general-purpose` agent was used instead,
explicitly instructed to follow the pharma-auditor's exact persona and
six review categories (folding in accessibility and deployment-readiness
as extensions of categories 6 and 3), read-only, no edits.

Overall verdict: **ready with minor fixes**. No blockers. Confirmed clean
(no changes needed): risk-calculation accuracy and boundary conditions
(exact match to `.claude/skills/pharma-risk/SKILL.md`), security (no
shell execution, no `.env`/secret access, no outbound network calls,
uploads validated before reaching pandas), and most of governance and
data-quality logic.

Should-fix items found, all fixed:
1. **`.xls` uploads crashed the whole dashboard instead of showing a
   specific rejection message.** `.xls` was an advertised, allowed
   upload extension, but every non-CSV upload was parsed with
   `engine="openpyxl"`, which cannot open the legacy binary `.xls`
   format and raises its own exception type — not one of the
   `(ParserError, UnicodeDecodeError, ValueError)` types the parser
   caught. That exception escaped into `app.py`'s generic
   `except Exception` handler, halting the entire app rather than
   producing the intended "this file could not be used" message.
   **Fix:** broadened the `except` in `src/upload.py::load_inventory_upload`
   to catch any parse failure and re-raise it as a `DataValidationError`
   with the original message. Added
   `test_unparseable_xls_raises_data_validation_error` to
   `tests/test_upload.py` to cover it.
2. **`docs/PROGRESS.md` had not been updated for Phase 3.** Fixed by this
   entry.
3. **Uploaded/derived data could remain in Streamlit's process-wide cache
   indefinitely**, which is stronger persistence than the
   "current session only" wording in `docs/GOVERNANCE.md` and the
   Governance tab implies (the underlying no-disk/no-external-service
   guarantee was never violated — only the cache lifetime). **Fix:**
   added a one-hour `ttl` to both `@st.cache_data` loaders in `app.py`.
4. No test exercised a real malformed/legacy `.xls` file, so finding 1
   went uncaught by the existing suite — fixed by the same new test
   noted in item 1.

One should-fix item was reviewed and deliberately **not** changed: the
audit flagged the six-filter sidebar as exceeding
`.claude/skills/professional-ui/SKILL.md`'s minimal filter example
("category, risk status, date range"). The Phase 3 task prompt explicitly
specified all six filters (Medicine, Category, Warehouse, Expiry-status,
Stock-status, Risk-level) by name; that explicit, specific instruction
takes precedence over the skill's generic illustrative example, so the
filter set was left as specified.

Nice-to-have items noted but not actioned (low severity, out of scope for
this pass): an Excel decompression-ratio DoS edge case bounded by the
existing 10 MB upload cap, and unpinned upper-bound versions in
`requirements.txt`.

`pytest` run after fixes: **174 passed, 0 failed** (up from 173; +1 test).

Phase 3 is complete. The dashboard, its tests, its config/doc files, and
the audit fixes above are the full scope of this session's work.

## Phase 3 Verification — Final End-to-End Validation
Status: Complete — 13/13 checks passed, no confirmed failures, no code changes

Ran a dedicated end-to-end validation pass against the full 13-point list
below, using `streamlit.testing.v1.AppTest` to drive the real `app.py` in
process (uploads, filter widgets, tab switches, download buttons) without
needing a browser, plus direct calls into `src/` for the boundary-condition
and disk-write checks, plus a full `pytest` run.

| # | Check | Result |
|---|---|---|
| 1 | Default synthetic CSV loads | Pass — 200 rows, correct lineage caption |
| 2 | CSV and Excel uploads work | Pass — both `.csv` and `.xlsx` uploads processed and reflected in the success message |
| 3 | Invalid files show clear errors | Pass — wrong-extension rejection (`tests/test_upload.py::test_wrong_extension_raises`) and malformed-content rejection (AppTest, uploading a garbage `.xls`) both raise a clear `DataValidationError` and the app falls back to the sample dataset rather than crashing |
| 4 | KPI values match the processed data | Pass — all six KPI values matched an independently-recomputed `apply_risk_engine()` result byte-for-byte |
| 5 | All filters work together | Pass — combined Warehouse + Risk Level selection (AND logic) produced the exact expected row count |
| 6 | Charts update when filters change | Pass — Plotly chart specs on the Executive Dashboard tab changed after applying a Risk Level filter |
| 7 | Expiry and stock-risk calculations are correct | Pass — re-verified the boundary cases (30/31-day expiry cutoff, stock exactly at reorder level, low stock, overstock) against `.claude/skills/pharma-risk/SKILL.md` |
| 8 | All three reports download correctly | Pass — all three `download_button`s are wired to the correct tab with the correct label, and the underlying CSV/CSV/Markdown content each one serialises was independently regenerated and checked (200 rows, 24 Critical rows, valid Markdown) |
| 9 | The "Project Analytics" moving line works | Pass — marquee markup contains the required text, `@keyframes`, and `animation` CSS |
| 10 | Reduced-motion accessibility is supported | Pass — `prefers-reduced-motion: reduce` sets `animation: none`; hover sets `animation-play-state: paused` |
| 11 | Governance and disclaimer content are visible | Pass — synthetic-data notice, no-medical-advice warning, calculation rules, and session-only-processing statement all present on the Governance tab |
| 12 | No data is stored permanently | Pass — `src/upload.py` contains no `open(`/`to_csv`/`to_excel` disk-write call; the only disk read anywhere is `src/data_loader.py` loading the bundled sample dataset, which is expected |
| 13 | All tests pass | Pass — `pytest` run: **174 passed, 0 failed** |

No confirmed failures were found, so no application code was changed in
this verification pass, per instructions ("fix only confirmed failures").
All dependencies in `requirements.txt` were already installed
(`streamlit` 1.63.0, `pandas` 3.0.5, `plotly` 7.0.0, `openpyxl` 3.1.5,
`pytest` 9.1.1); nothing needed to be installed.
