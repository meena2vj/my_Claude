# Data Dictionary — Pharma Project Analytics

This document describes every column in `data/pharma_inventory.csv` (the
raw source columns) and every column added by the risk engine
(`src/risk_engine.py`). All classification rules are deterministic
Python — no LLM or ML is used for any calculation (per
`docs/GOVERNANCE.md`, "Calculation Transparency").

## Source Columns (`data/pharma_inventory.csv`)

| Column | Type | Description | Example | Notes |
|---|---|---|---|---|
| `Batch_ID` | string | Unique identifier for a manufactured batch | `BATCH-0001` | May repeat if a batch was accidentally double-entered — see [Duplicate Records](#duplicate-records) and [Duplicate Batch_ID](#duplicate-batch_id) |
| `Medicine_Name` | string | Generic medicine name and strength | `Paracetamol 500mg` | Synthetic data only, no real product/brand claims |
| `Category` | string | Therapeutic category | `Analgesic` | Free text, not a controlled vocabulary in this phase |
| `Manufacturer` | string | Fictional manufacturer name | `MediCore Pharma` | Synthetic; not a real company |
| `Manufacturing_Date` | date (`YYYY-MM-DD`) | Date the batch was manufactured | `2025-01-01` | |
| `Expiry_Date` | date (`YYYY-MM-DD`) | Date the batch expires | `2027-01-01` | Used with today's date to compute `Days_To_Expiry` |
| `Current_Stock` | integer | Units currently in stock | `250` | Should never be negative; see [Negative Stock](#negative-stock) |
| `Reorder_Level` | integer | Stock threshold below which reordering is needed | `50` | |
| `Maximum_Stock` | integer | Stock threshold above which the warehouse is overstocked | `300` | |
| `Unit_Price` | float | Price per unit | `5.00` | Currency-agnostic |
| `Warehouse` | string | Storage location code | `WH-North` | One of `WH-North`, `WH-South`, `WH-East`, `WH-West`, `WH-Central` in the synthetic dataset |
| `Critical_Medicine` | string (`Yes`/`No`) | Whether the medicine is clinically critical (e.g. life-sustaining, no ready substitute) | `Yes` | Drives the Critical Risk rule below; not a dosage/medical field |

This dataset contains **no patient or personal data** — every field is
inventory/operational-level, per `docs/GOVERNANCE.md`.

## Derived Columns (`src/risk_engine.py`)

All derived columns are computed by `risk_engine.apply_risk_engine()`.
Every rule below is implemented as a plain, inspectable Python
function — see the module docstring in `src/risk_engine.py` for the
exact code paths.

| Column | Type | Description |
|---|---|---|
| `Days_To_Expiry` | integer or missing | `Expiry_Date - reference_date` in days. Missing if `Expiry_Date` is blank or unparseable. |
| `Expiry_Status` | `EXPIRED` \| `EXPIRING_SOON` \| `SAFE` \| `UNKNOWN` | See [Expiry Status](#expiry-status) below. |
| `Stock_Status` | `LOW_STOCK` \| `OVERSTOCK` \| `NORMAL` \| `INVALID` \| `UNKNOWN` | See [Stock Status](#stock-status) below. |
| `Inventory_Value` | float or missing | `Current_Stock * Unit_Price`, rounded to 2 decimals. Missing if either input is blank/unparseable or `Current_Stock` is negative. |
| `Risk_Score` | integer, 0–100 | Additive point total. See [Risk Score](#risk-score) below. |
| `Risk_Level` | `Critical` \| `High` \| `Medium` \| `Low` | Threshold on `Risk_Score`. See [Risk Level](#risk-level) below. |
| `Recommended_Action` | string | Fixed-template next step derived from the statuses above. See [Recommended Action](#recommended-action) below. |

### Expiry Status

Defined by `.claude/skills/pharma-risk/SKILL.md` (boundaries inclusive
as written):

| Condition | Status |
|---|---|
| `Days_To_Expiry < 0` | `EXPIRED` |
| `0 <= Days_To_Expiry <= 30` | `EXPIRING_SOON` |
| `Days_To_Expiry > 30` | `SAFE` |
| `Expiry_Date` missing or unparseable | `UNKNOWN` |

### Stock Status

Defined by `.claude/skills/pharma-risk/SKILL.md`, extended with explicit
outcomes for missing/invalid inputs (the skill only defines the
clean-data case):

| Condition | Status |
|---|---|
| `Current_Stock` missing, unparseable, or negative | `INVALID` |
| `Reorder_Level` or `Maximum_Stock` missing/unparseable | `UNKNOWN` |
| `Current_Stock < Reorder_Level` | `LOW_STOCK` |
| `Current_Stock > Maximum_Stock` | `OVERSTOCK` |
| otherwise | `NORMAL` |

`Current_Stock` exactly equal to `Reorder_Level` or exactly equal to
`Maximum_Stock` is `NORMAL` (strict inequality per the skill).

### Critical Risk (boolean, used internally to compute Risk_Score/Recommended_Action)

Defined by `.claude/skills/pharma-risk/SKILL.md`: an item is Critical
Risk when `Critical_Medicine = Yes` **and** (`Expiry_Status = EXPIRED`
**or** `Stock_Status = LOW_STOCK`).

### Risk Score

**Phase 2 extension** layered on top of the two rules above so that a
priority order can be assigned without inventing new risk categories.
Additive, capped at 100:

| Component | Value |
|---|---|
| `Expiry_Status = EXPIRED` | +50 |
| `Expiry_Status = EXPIRING_SOON` | +30 |
| `Expiry_Status = UNKNOWN` | +20 (a data problem is a risk in itself — it must be reviewed, not ignored) |
| `Expiry_Status = SAFE` | +0 |
| `Stock_Status = LOW_STOCK` | +30 |
| `Stock_Status = OVERSTOCK` | +15 |
| `Stock_Status = INVALID` or `UNKNOWN` | +20 |
| `Stock_Status = NORMAL` | +0 |
| Critical Risk is true (see above) | +30 |

### Risk Level

**Phase 2 extension.** Thresholds on `Risk_Score`:

| Risk_Score | Risk_Level |
|---|---|
| `>= 60` | `Critical` |
| `40–59` | `High` |
| `20–39` | `Medium` |
| `< 20` | `Low` |

These thresholds are chosen deliberately so that every combination the
pharma-risk skill calls "Critical Risk" lands in `Risk_Level = Critical`
(`EXPIRED` + critical = 80, `LOW_STOCK` + critical = 60), while a single
non-critical issue lands lower (`EXPIRED` alone = 50 → `High`;
`LOW_STOCK`/`EXPIRING_SOON` alone = 30 → `Medium`).

### Recommended Action

**Phase 2 extension.** A fixed-template sentence (or `;`-joined list of
sentences) built from the statuses above — never freeform or
LLM-generated text:

- Data-integrity notes ("Verify batch data - ...") always come first,
  since acting on a classification derived from bad data is unsafe.
- Then an expiry-based action (`EXPIRED` → remove immediately;
  `EXPIRING_SOON` → prioritize distribution).
- Then a stock-based action (`LOW_STOCK` → reorder; `OVERSTOCK` →
  reduce future orders).
- If Critical Risk is true, `"URGENT - flag for human review (critical
  medicine)"` is prepended — per `docs/GOVERNANCE.md` ("Human Review of
  Critical-Risk Results"), this is a flag for a person, not an
  automated action.
- If none of the above apply: `"No action needed - monitor routinely"`.

## Data Quality Dimensions (`src/data_quality.py`)

`data/pharma_inventory.csv` contains controlled, known examples of each
dimension below so the checks can be demonstrated and tested:

| Dimension | How it's detected | Controlled examples in the dataset |
|---|---|---|
| Missing values | Blank cell or `NaN` in any required column | 15 rows, one missing field each, spread across most columns |
| Duplicate records | Two or more rows identical across every column (`check_duplicate_rows`) | 5 exact duplicate pairs (10 rows total) |
| Duplicate Batch_ID | A non-blank `Batch_ID` appears on more than one row, whether or not the other columns agree (`check_duplicate_batch_ids`) — catches a Batch_ID reused with *conflicting* data, which an exact-row check misses, since it necessarily also flags every exact duplicate pair | Same 5 duplicate pairs as above (10 rows); any row sharing a Batch_ID with different other data would also be caught here |
| Invalid dates | `Manufacturing_Date`/`Expiry_Date` present but unparseable, or `Manufacturing_Date` after `Expiry_Date` | 10 rows (5 malformed date strings, 5 with manufacturing after expiry) |
| Negative stock | `Current_Stock` parses to a number `< 0` | 10 rows |

`check_duplicate_rows` and `check_duplicate_batch_ids` are deliberately
separate checks: the former only flags an accidental double-entry of
*identical* data, while the latter flags the more serious integrity
problem of the same Batch_ID being reused with *different* data, where
it is ambiguous which row is authoritative.

Detected issues are **reported, never silently repaired or dropped**
(`docs/GOVERNANCE.md`, "File Validation"). The risk engine still
computes a classification for rows with these issues, using the
explicit `UNKNOWN`/`INVALID` outcomes documented above, so a bad row is
surfaced for review rather than causing a crash or a guessed value.

## Regenerating the dataset

`scripts/generate_dataset.py` regenerates `data/pharma_inventory.csv`
deterministically (fixed random seed, fixed anchor date). Re-run it if
the dataset needs to be recreated:

```
python3 scripts/generate_dataset.py
```
