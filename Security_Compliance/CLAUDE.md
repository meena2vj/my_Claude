# CLAUDE.md — Pharma Data Security & Compliance (Synthetic Data)

## Purpose
This project handles pharmaceutical and clinical data for demo, analytics, and model validation using synthetic data only. Do not use real patient, product, or clinical records. The operating model must satisfy privacy, governance, and security expectations for regulated healthcare and life-science workflows.

## Scope
- Synthetic patient, site, product, and adverse-event data
- Analytics and model monitoring for compliance and risk use cases
- Lightweight web deployment with Streamlit
- Internal-only demo environments and low-risk research workflows

## Skills
Use the following operating skills when working on this project:

- Data minimization: keep only the fields necessary for the use case.
- Privacy by design: use synthetic IDs, de-identification, and no direct identifiers.
- Security review: verify secrets handling, access controls, and dependency security.
- Compliance interpretation: align with HIPAA, GDPR, GxP, and 21 CFR Part 11 expectations where relevant.
- Model governance: document data lineage, assumptions, validation, and limitations.
- Deployment hygiene: prefer minimal, auditable, and reproducible deployment patterns.

## Subagents
Use specialized subagents for review work:

- compliance-reviewer: validates policies, retention, consent assumptions, and auditability.
- security-auditor: checks dependency risk, secrets handling, auth, and secure defaults.
- data-quality-analyst: confirms schema validity, null logic, drift detection, and synthetic data realism.
- model-governance-reviewer: verifies documentation, approvals, and risk classification.
- deployment-ops: validates Streamlit startup, environment variables, and runtime security.

When a task touches data handling, governance, or model output, involve the relevant subagent before finalizing changes.

## Guardrails
These rules are mandatory.

- Never use real patient data, PHI, or identifiable clinical details.
- Use synthetic data only for local development, demos, and testing.
- Store secrets in environment variables or secret stores; never in source files.
- Do not send data to third-party unapproved services or public notebooks.
- Follow least-privilege access; do not grant broad admin access for demo work.
- Log access to sensitive datasets and models; maintain traceability.
- Keep all code, config, and data generation reproducible and version-controlled.
- Do not generate outputs that imply real-world patient outcomes or regulated decisions.
- Validate model results against synthetic ground truth and clearly label as demo-only.
- If a business requirement needs production data, escalate to compliance approval before proceeding.

## Hooks
Use the following hooks in the development workflow.

### Pre-commit hooks
- Run linting and formatting.
- Block changes to tracked secrets or .env files.
- Validate schema names and required fields for data files.
- Ensure synthetic data files are clearly labeled as synthetic.

### CI hooks
- Run pytest on all data validation and compliance checks.
- Run bandit or equivalent dependency/security scan.
- Check for new packages with known vulnerabilities.
- Verify environment config does not contain hardcoded secrets.

### Example commands
```bash
python -m pytest -q
python -m bandit -r .
python -m pip-audit
```

## Test Set
Use a minimal but representative synthetic test set for pharma workflows.

### Required synthetic datasets
- Patients: patient_id, age_band, sex, region, trial_arm, enrollment_date
- Labs: patient_id, test_name, result_value, unit, collected_at
- Adverse events: patient_id, event_type, seriousness, onset_date, resolved_flag
- Sites: site_id, region, investigator, status
- Products: product_id, product_name, therapeutic_area, market_status
- Safety reports: report_id, product_id, patient_id, report_type, route, risk_flag

### Test coverage
- Schema validation: all required columns exist and types are correct.
- Integrity checks: no duplicate patient IDs or malformed dates.
- Privacy tests: all IDs are synthetic, no literal names or direct identifiers.
- Access tests: role-based permissions block unauthorized views.
- Drift tests: data distribution remains within expected ranges.
- Model validation: output remains explainable and limited to demo use.

### Example validation checklist
- No direct identifiers present
- Date ranges are realistic and non-production
- Missing values are handled consistently
- Safety flags are defined by policy, not ad hoc rules
- All outputs are tagged as synthetic and non-clinical

## Governance
This project must follow a lightweight governance model suitable for internal demo and research environments.

### Roles
- Data owner: defines business purpose and permitted use of the dataset.
- Data steward: validates schema, quality, and lineage.
- Security reviewer: confirms secret handling and access controls.
- Model owner: responsible for model limitations, validation, and deployment approval.
- Compliance reviewer: checks risk classification and policy fit.

### Required controls
- Data classification: internal demo / synthetic / non-production
- Retention policy: keep only as long as needed for validation or demos
- Access policy: least privilege, MFA for privileged access, no shared accounts
- Audit trail: record who accessed data and when
- Change control: every model or pipeline change should be reviewed and documented
- Approval gates: no model deployment without owner sign-off

### Documentation expectations
- Maintain a dataset dictionary
- Record assumptions, exclusions, and synthetic-data generation method
- Keep a simple model card or risk note for each feature or model
- Record any known limitations and prohibited uses

## Streamlit Deployment (Lightweight)
Deploy only in a controlled non-production environment.

### Deployment principles
- Use a minimal Streamlit app with public-safe synthetic data only.
- Store all credentials in environment variables.
- Enable HTTPS and restrict network exposure.
- Do not expose admin endpoints or raw data exports publicly.
- Add a visible banner stating: “Synthetic data only; not for clinical or production use.”

### Example app configuration
```python
import os
import streamlit as st

st.set_page_config(page_title="Pharma Compliance Demo", layout="wide")

st.warning("Synthetic data only. This application is for demonstration and compliance review, not clinical use.")

# Example environment variables
API_TOKEN = os.getenv("APP_API_TOKEN")
if not API_TOKEN:
    st.error("Missing APP_API_TOKEN")
```

### Recommended run pattern
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Deployment checklist
- App uses synthetic data only
- No secrets in repo or logs
- Authentication enabled for non-local access
- Access logs enabled
- Data export disabled or restricted
- App clearly labels data as synthetic and demo-only

## Decision Rules
- If a task involves real patient, product, or clinical data, stop and escalate.
- If a dependency or service is not approved, do not install or connect it.
- If a model output can influence regulated decisions, require governance review before use.
- If the data is not clearly synthetic, treat it as restricted and do not process it.

## Summary
This project is a privacy-safe, governance-aware pharma data environment built around synthetic data. The default posture is: minimize, isolate, document, and verify before any deployment.
