"""Schema, integrity, privacy, drift, and access-control checks.

Shared by the Streamlit app (Drift Monitoring / Overview tabs) and the pytest
suite in tests/, so a rule is defined once and enforced in both places.
"""
import re
from typing import Iterable

import pandas as pd

REQUIRED_SCHEMAS: dict[str, list[str]] = {
    "patients": ["patient_id", "age_band", "sex", "region", "trial_arm", "enrollment_date"],
    "labs": ["patient_id", "test_name", "result_value", "unit", "collected_at"],
    "adverse_events": ["patient_id", "event_type", "seriousness", "onset_date", "resolved_flag"],
    "sites": ["site_id", "region", "investigator", "status"],
    "products": ["product_id", "product_name", "therapeutic_area", "market_status"],
    "safety_reports": ["report_id", "product_id", "patient_id", "report_type", "route", "risk_flag"],
}

ID_PATTERNS: dict[str, re.Pattern] = {
    "patient_id": re.compile(r"^PT-\d{6}$"),
    "site_id": re.compile(r"^SITE-\d{3}$"),
    "product_id": re.compile(r"^PRD-\d{3}$"),
    "report_id": re.compile(r"^SR-\d{6}$"),
    "investigator": re.compile(r"^INV-\d{3}$"),
}

# Columns that would indicate a direct identifier leaked into a synthetic dataset.
DIRECT_IDENTIFIER_COLUMNS = {
    "name", "first_name", "last_name", "full_name", "email", "phone",
    "ssn", "address", "dob", "date_of_birth", "mrn", "national_id",
}

DATE_COLUMNS = {
    "patients": ["enrollment_date"],
    "labs": ["collected_at"],
    "adverse_events": ["onset_date"],
}

# Role -> ordered list of tab names visible to that role (least privilege).
ROLE_TABS: dict[str, list[str]] = {
    "viewer": ["Overview", "Adverse Events", "Sites & Products"],
    "analyst": [
        "Overview", "Patients", "Labs", "Adverse Events",
        "Sites & Products", "Drift Monitoring", "Model Validation",
    ],
    "admin": [
        "Overview", "Patients", "Labs", "Adverse Events", "Safety Reports",
        "Sites & Products", "Drift Monitoring", "Model Validation", "Audit Log",
    ],
}

# Roles allowed to export an aggregated (never raw patient-level) CSV.
EXPORT_ROLES = {"analyst", "admin"}


def tabs_for_role(role: str) -> list[str]:
    return ROLE_TABS.get(role, [])


def can_export(role: str) -> bool:
    return role in EXPORT_ROLES


def validate_schema(name: str, df: pd.DataFrame) -> list[str]:
    """Returns a list of problems; empty list means the schema is valid."""
    problems = []
    required = REQUIRED_SCHEMAS.get(name, [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        problems.append(f"{name}: missing required columns {missing}")
    return problems


def validate_integrity(name: str, df: pd.DataFrame) -> list[str]:
    problems = []
    id_col = {"patients": "patient_id", "sites": "site_id", "products": "product_id",
              "safety_reports": "report_id"}.get(name)
    if id_col and id_col in df.columns and name in ("patients", "sites", "products"):
        dup_count = df[id_col].duplicated().sum()
        if dup_count:
            problems.append(f"{name}: {dup_count} duplicate {id_col} values")

    for date_col in DATE_COLUMNS.get(name, []):
        if date_col in df.columns:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            bad = parsed.isna().sum()
            if bad:
                problems.append(f"{name}: {bad} malformed values in {date_col}")
    return problems


def validate_privacy(name: str, df: pd.DataFrame) -> list[str]:
    problems = []
    leaked = DIRECT_IDENTIFIER_COLUMNS.intersection({c.lower() for c in df.columns})
    if leaked:
        problems.append(f"{name}: direct identifier columns present {sorted(leaked)}")

    for id_col, pattern in ID_PATTERNS.items():
        if id_col in df.columns:
            invalid = ~df[id_col].astype(str).str.match(pattern)
            if invalid.any():
                problems.append(f"{name}: {invalid.sum()} values in {id_col} don't match synthetic ID pattern")
    return problems


def validate_drift(current: dict, expected: dict, tolerance: float = 3.0) -> list[str]:
    """Flags a test_name whose current mean has drifted more than `tolerance`
    standard deviations away from the expected (generation-time) mean."""
    problems = []
    for test_name, exp in expected.items():
        cur = current.get(test_name)
        if not cur or exp.get("std", 0) == 0:
            continue
        z = abs(cur["mean"] - exp["mean"]) / exp["std"]
        if z > tolerance:
            problems.append(f"{test_name}: mean drifted {z:.1f} std devs from baseline")
    return problems


def run_all_checks(datasets: dict[str, pd.DataFrame]) -> list[str]:
    problems: list[str] = []
    for name, df in datasets.items():
        problems += validate_schema(name, df)
        problems += validate_integrity(name, df)
        problems += validate_privacy(name, df)
    return problems
