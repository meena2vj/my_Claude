"""Generates the synthetic pharma datasets required by CLAUDE.md's Test Set section.

No real patient, product, or clinical data is used or referenced. All identifiers,
names, and dates are procedurally generated from a fixed seed. Safe to delete and
re-run at any time — nothing here is authoritative source data.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

REGIONS = ["NA", "EU", "APAC", "LATAM"]
AGE_BANDS = ["18-30", "31-45", "46-60", "61-75", "76+"]
SEXES = ["F", "M", "U"]
TRIAL_ARMS = ["Arm-A", "Arm-B", "Placebo"]
THERAPEUTIC_AREAS = ["Oncology", "Cardiology", "Neurology", "Immunology", "Endocrinology"]
MARKET_STATUSES = ["Investigational", "Approved", "Withdrawn"]
SITE_STATUSES = ["Active", "Recruiting", "Closed"]
EVENT_TYPES = ["Headache", "Nausea", "Fatigue", "Rash", "Fever", "Dizziness", "Vomiting"]
REPORT_TYPES = ["Spontaneous", "Clinical Trial", "Literature"]
ROUTES = ["Oral", "IV", "Topical", "Subcutaneous"]

LAB_TESTS = {
    # test_name: (unit, normal_mean, normal_std, abnormal_shift)
    "ALT": ("U/L", 25, 8, 40),
    "AST": ("U/L", 24, 7, 35),
    "Hemoglobin": ("g/dL", 13.5, 1.2, -3.5),
    "WBC": ("10^9/L", 6.5, 1.5, 5.0),
    "Creatinine": ("mg/dL", 0.9, 0.2, 1.2),
}

N_SITES = 40
N_PRODUCTS = 15
N_PATIENTS = 500
N_LABS_PER_PATIENT_RANGE = (3, 8)
N_AE_PER_PATIENT_RANGE = (0, 3)
N_SAFETY_REPORTS = 300

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 6, 30)


def _random_date(rng: np.random.Generator, start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=int(rng.integers(0, delta_days + 1)))


def _seed() -> int:
    return int(os.getenv("SYNTHETIC_DATA_SEED", "42"))


def generate_sites(rng: np.random.Generator) -> pd.DataFrame:
    return pd.DataFrame({
        "site_id": [f"SITE-{i:03d}" for i in range(1, N_SITES + 1)],
        "region": rng.choice(REGIONS, N_SITES),
        "investigator": [f"INV-{rng.integers(1, 999):03d}" for _ in range(N_SITES)],
        "status": rng.choice(SITE_STATUSES, N_SITES, p=[0.6, 0.3, 0.1]),
        "synthetic": True,
    })


def generate_products(rng: np.random.Generator) -> pd.DataFrame:
    return pd.DataFrame({
        "product_id": [f"PRD-{i:03d}" for i in range(1, N_PRODUCTS + 1)],
        "product_name": [f"Compound-{chr(65 + i % 26)}{i:02d}" for i in range(N_PRODUCTS)],
        "therapeutic_area": rng.choice(THERAPEUTIC_AREAS, N_PRODUCTS),
        "market_status": rng.choice(MARKET_STATUSES, N_PRODUCTS, p=[0.5, 0.35, 0.15]),
        "synthetic": True,
    })


def generate_patients(rng: np.random.Generator) -> pd.DataFrame:
    return pd.DataFrame({
        "patient_id": [f"PT-{i:06d}" for i in range(1, N_PATIENTS + 1)],
        "age_band": rng.choice(AGE_BANDS, N_PATIENTS),
        "sex": rng.choice(SEXES, N_PATIENTS, p=[0.48, 0.48, 0.04]),
        "region": rng.choice(REGIONS, N_PATIENTS),
        "trial_arm": rng.choice(TRIAL_ARMS, N_PATIENTS),
        "enrollment_date": [_random_date(rng, START_DATE, END_DATE) for _ in range(N_PATIENTS)],
        "synthetic": True,
    })


def generate_labs(rng: np.random.Generator, patients: pd.DataFrame, abnormal_patients: set) -> pd.DataFrame:
    rows = []
    for patient_id in patients["patient_id"]:
        n_labs = int(rng.integers(*N_LABS_PER_PATIENT_RANGE))
        is_abnormal = patient_id in abnormal_patients
        for _ in range(n_labs):
            test_name = rng.choice(list(LAB_TESTS.keys()))
            unit, mean, std, shift = LAB_TESTS[test_name]
            base = rng.normal(mean, std)
            value = base + shift * rng.uniform(0.6, 1.0) if is_abnormal and rng.random() < 0.6 else base
            rows.append({
                "patient_id": patient_id,
                "test_name": test_name,
                "result_value": round(float(value), 2),
                "unit": unit,
                "collected_at": _random_date(rng, START_DATE, END_DATE),
                "synthetic": True,
            })
    return pd.DataFrame(rows)


def generate_adverse_events(rng: np.random.Generator, patients: pd.DataFrame, serious_patients: set) -> pd.DataFrame:
    rows = []
    for patient_id in patients["patient_id"]:
        n_ae = int(rng.integers(*N_AE_PER_PATIENT_RANGE))
        is_serious_patient = patient_id in serious_patients
        for _ in range(n_ae):
            seriousness = "Serious" if (is_serious_patient and rng.random() < 0.7) else rng.choice(
                ["Serious", "Non-serious"], p=[0.1, 0.9]
            )
            rows.append({
                "patient_id": patient_id,
                "event_type": rng.choice(EVENT_TYPES),
                "seriousness": seriousness,
                "onset_date": _random_date(rng, START_DATE, END_DATE),
                "resolved_flag": bool(rng.random() < (0.6 if seriousness == "Serious" else 0.9)),
                "synthetic": True,
            })
    return pd.DataFrame(rows)


def generate_safety_reports(
    rng: np.random.Generator,
    patients: pd.DataFrame,
    products: pd.DataFrame,
    serious_patients: set,
    abnormal_patients: set,
) -> pd.DataFrame:
    sample_patients = rng.choice(patients["patient_id"], N_SAFETY_REPORTS, replace=True)
    sample_products = rng.choice(products["product_id"], N_SAFETY_REPORTS, replace=True)
    risk_flags = []
    for patient_id in sample_patients:
        risk_score = 0.15
        if patient_id in serious_patients:
            risk_score += 0.45
        if patient_id in abnormal_patients:
            risk_score += 0.25
        risk_flags.append(bool(rng.random() < risk_score))
    return pd.DataFrame({
        "report_id": [f"SR-{i:06d}" for i in range(1, N_SAFETY_REPORTS + 1)],
        "product_id": sample_products,
        "patient_id": sample_patients,
        "report_type": rng.choice(REPORT_TYPES, N_SAFETY_REPORTS, p=[0.5, 0.35, 0.15]),
        "route": rng.choice(ROUTES, N_SAFETY_REPORTS),
        "risk_flag": risk_flags,
        "synthetic": True,
    })


def generate_all(seed: int | None = None) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed if seed is not None else _seed())

    sites = generate_sites(rng)
    products = generate_products(rng)
    patients = generate_patients(rng)

    serious_patients = set(rng.choice(patients["patient_id"], size=int(N_PATIENTS * 0.15), replace=False))
    abnormal_patients = set(rng.choice(patients["patient_id"], size=int(N_PATIENTS * 0.2), replace=False))

    labs = generate_labs(rng, patients, abnormal_patients)
    adverse_events = generate_adverse_events(rng, patients, serious_patients)
    safety_reports = generate_safety_reports(rng, patients, products, serious_patients, abnormal_patients)

    return {
        "sites": sites,
        "products": products,
        "patients": patients,
        "labs": labs,
        "adverse_events": adverse_events,
        "safety_reports": safety_reports,
    }


def _expected_ranges(datasets: dict[str, pd.DataFrame]) -> dict:
    labs = datasets["labs"]
    ranges = {}
    for test_name in LAB_TESTS:
        values = labs.loc[labs["test_name"] == test_name, "result_value"]
        ranges[test_name] = {
            "mean": round(float(values.mean()), 2),
            "std": round(float(values.std()), 2),
            "min": round(float(values.min()), 2),
            "max": round(float(values.max()), 2),
        }
    return ranges


def write_all(datasets: dict[str, pd.DataFrame] | None = None) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    datasets = datasets or generate_all()
    for name, df in datasets.items():
        df.to_csv(DATA_DIR / f"{name}.csv", index=False)

    with open(DATA_DIR / "expected_ranges.json", "w") as f:
        json.dump(_expected_ranges(datasets), f, indent=2)

    (DATA_DIR / "README_SYNTHETIC.txt").write_text(
        "All files in this directory are procedurally generated synthetic data.\n"
        "No real patient, product, or clinical records are present.\n"
        "Regenerate at any time with: python generate_synthetic_data.py\n"
    )


if __name__ == "__main__":
    write_all()
    print(f"Synthetic data written to {DATA_DIR}")
