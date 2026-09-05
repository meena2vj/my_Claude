---
name: pharma-risk
description: Risk classification rules for medicine inventory/expiry analytics (expiry status, stock status, critical risk).
---

# Pharma Risk Classification Rules

Use these rules whenever computing or explaining expiry/stock risk for the
Pharma Project Analytics dashboard. These are the only rules that define
risk in this project — do not invent additional risk categories.

## Expiry Status
Given `expiry_date` and `today`:
- `expiry_date < today` → **EXPIRED**
- `today <= expiry_date <= today + 30 days` → **EXPIRING SOON**
- `expiry_date > today + 30 days` → **SAFE**

## Stock Status
Given `current_stock`, `reorder_level`, `max_stock`:
- `current_stock < reorder_level` → **LOW STOCK**
- `current_stock > max_stock` → **OVERSTOCK**
- otherwise → normal (no stock flag)

## Critical Risk
An item is **CRITICAL RISK** when either:
- Expiry status is EXPIRED, or
- Stock status is LOW STOCK

AND the item is flagged as a critical medicine (`is_critical` = true).

## Notes
- Boundary values are inclusive as written above (exactly 30 days to
  expiry = EXPIRING SOON; stock exactly at reorder level = not LOW STOCK;
  stock exactly at max_stock = not OVERSTOCK).
- Every classification must be traceable to these rules — no hidden
  thresholds or scoring.
- CRITICAL RISK items must be flagged for human review, never acted on
  automatically (see `docs/GOVERNANCE.md`).
