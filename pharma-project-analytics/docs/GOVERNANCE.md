# Data Governance — Pharma Project Analytics

## Synthetic Operational Data Only
All data used in development, testing, and demonstration must be synthetic
or clearly de-identified operational sample data. No production or
real-world sourced data may be loaded into this application.

## No Patient or Personal Data
The application must never accept, store, or display patient names, IDs,
contact details, or any personally identifiable information (PII). Input
files must only contain medicine/inventory-level fields (e.g. medicine
name, batch, quantity, expiry date, reorder level).

## No Diagnosis, Dosage or Medical Advice
This tool performs inventory and expiry analytics only. It must never:
- Suggest a diagnosis or treatment.
- Recommend or calculate dosage.
- Offer medical advice of any kind.
Any such content found in the UI or logic must be removed immediately.

## Data Minimisation
Only load and retain the columns required for the analytics in scope
(medicine name, category, batch, quantity, reorder level, max stock,
expiry date, critical flag). Drop or ignore any extra columns from
uploaded files rather than storing them.

## File Validation
All uploaded files must be validated before use:
- Correct file type/extension (e.g. CSV).
- Required columns present with expected types.
- Reasonable file size limits enforced.
- Reject and clearly report invalid files; never attempt to "guess" or
  silently repair malformed data.

## Calculation Transparency
Every risk classification (EXPIRED, EXPIRING SOON, SAFE, LOW STOCK,
OVERSTOCK, CRITICAL RISK) must be based on a documented, inspectable rule
(see `.claude/skills/pharma-risk/SKILL.md`). No opaque scoring or ML-based
risk logic without an equivalent transparent explanation shown to the
user.

## Data Lineage
The dashboard must make clear where displayed data came from (e.g. the
uploaded file name and row count) and when it was processed, so results
can be traced back to their source input.

## Session-Only Processing
Uploaded data is processed in memory for the current session only. No
uploaded file or derived data is persisted to disk or any external
service beyond the running session.

## Human Review of Critical-Risk Results
Any item classified as CRITICAL RISK must be flagged for human review
before any downstream action is taken. The application only surfaces the
classification — it does not take automated action on critical items.

## Application Limitations
This dashboard is a decision-support aid, not a source of truth. It:
- Only reflects the accuracy and completeness of the uploaded data.
- Does not perform clinical, regulatory, or compliance validation.
- Should not be the sole basis for inventory or safety decisions.
