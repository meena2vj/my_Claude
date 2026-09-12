"""Loads synthetic datasets, generating them on first run if data/ is empty."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import generate_synthetic_data as gen

DATA_DIR = Path(__file__).parent.parent / "data"
DATASET_NAMES = ["patients", "labs", "adverse_events", "sites", "products", "safety_reports"]


def ensure_data_exists() -> None:
    if not DATA_DIR.exists() or not (DATA_DIR / "patients.csv").exists():
        gen.write_all()


@st.cache_data(show_spinner="Loading synthetic datasets...")
def load_datasets() -> dict[str, pd.DataFrame]:
    ensure_data_exists()
    return {name: pd.read_csv(DATA_DIR / f"{name}.csv") for name in DATASET_NAMES}


@st.cache_data
def load_expected_ranges() -> dict:
    ensure_data_exists()
    with open(DATA_DIR / "expected_ranges.json") as f:
        return json.load(f)
