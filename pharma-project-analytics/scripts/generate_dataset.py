"""Reproducible generator for the synthetic pharma inventory dataset.

Produces data/pharma_inventory.csv with 200 rows: 195 unique batch records
plus 5 exact duplicate rows. All data is synthetic (no real manufacturers,
patients, or products) per docs/GOVERNANCE.md.

Rows are generated in controlled blocks so the dataset always contains a
known number of each edge case required for Phase 2 testing:
  - expired batches
  - batches expiring within 30 days
  - low stock
  - overstock
  - rows with missing values
  - rows with invalid/malformed dates
  - rows with negative stock
  - exact duplicate records
  - clean baseline rows

Re-running this script with the same ANCHOR_DATE reproduces the same file
(random seed is fixed).
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42
ANCHOR_DATE = date(2026, 9, 5)  # "today" the dataset is generated relative to

COLUMNS = [
    "Batch_ID",
    "Medicine_Name",
    "Category",
    "Manufacturer",
    "Manufacturing_Date",
    "Expiry_Date",
    "Current_Stock",
    "Reorder_Level",
    "Maximum_Stock",
    "Unit_Price",
    "Warehouse",
    "Critical_Medicine",
]

MEDICINES = [
    ("Paracetamol 500mg", "Analgesic"),
    ("Ibuprofen 400mg", "Analgesic"),
    ("Diclofenac Gel", "Analgesic"),
    ("Amoxicillin 250mg", "Antibiotic"),
    ("Azithromycin 500mg", "Antibiotic"),
    ("Ciprofloxacin 500mg", "Antibiotic"),
    ("Doxycycline 100mg", "Antibiotic"),
    ("Metronidazole 400mg", "Antibiotic"),
    ("Oseltamivir 75mg", "Antiviral"),
    ("Acyclovir 400mg", "Antiviral"),
    ("Metformin 500mg", "Antidiabetic"),
    ("Gliclazide 80mg", "Antidiabetic"),
    ("Insulin Glargine", "Antidiabetic"),
    ("Atorvastatin 10mg", "Cardiovascular"),
    ("Simvastatin 20mg", "Cardiovascular"),
    ("Amlodipine 5mg", "Cardiovascular"),
    ("Losartan 50mg", "Cardiovascular"),
    ("Enalapril 10mg", "Cardiovascular"),
    ("Clopidogrel 75mg", "Cardiovascular"),
    ("Warfarin 5mg", "Cardiovascular"),
    ("Hydrochlorothiazide 25mg", "Cardiovascular"),
    ("Cetirizine 10mg", "Antihistamine"),
    ("Loratadine 10mg", "Antihistamine"),
    ("Omeprazole 20mg", "Gastrointestinal"),
    ("Pantoprazole 40mg", "Gastrointestinal"),
    ("Ranitidine 150mg", "Gastrointestinal"),
    ("Ondansetron 4mg", "Gastrointestinal"),
    ("Salbutamol Inhaler", "Respiratory"),
    ("Montelukast 10mg", "Respiratory"),
    ("Vitamin C 1000mg", "Vitamin/Supplement"),
    ("Vitamin D3 1000IU", "Vitamin/Supplement"),
    ("Folic Acid 5mg", "Vitamin/Supplement"),
    ("Fluconazole 150mg", "Antifungal"),
    ("Clotrimazole Cream", "Antifungal"),
    ("Levothyroxine 50mcg", "Other"),
    ("Prednisolone 5mg", "Other"),
]

MANUFACTURERS = [
    "MediCore Pharma",
    "Global Health Labs",
    "Sunrise Biotech",
    "Vertex Pharmaceuticals Ltd",
    "NovaCure Industries",
    "PharmaGen Inc",
    "BlueCross Formulations",
    "Zenith Life Sciences",
    "Aurora Meds Co",
    "Crestline Pharma",
]

WAREHOUSES = ["WH-North", "WH-South", "WH-East", "WH-West", "WH-Central"]

CRITICAL_CHOICES_WEIGHTED = ["Yes"] * 3 + ["No"] * 7

MISSING_TARGET_COLUMNS = [
    "Medicine_Name",
    "Category",
    "Manufacturer",
    "Current_Stock",
    "Reorder_Level",
    "Maximum_Stock",
    "Unit_Price",
    "Warehouse",
    "Critical_Medicine",
    "Expiry_Date",
    "Manufacturing_Date",
]

INVALID_DATE_STRINGS = [
    "2026-13-45",
    "31/02/2026",
    "not-a-date",
    "2026/33/01",
    "0000-00-00",
]


def _rng() -> random.Random:
    return random.Random(SEED)


def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _base_batch(rng: random.Random, idx: int) -> dict:
    """A clean, plausible, internally-consistent batch record."""
    name, category = rng.choice(MEDICINES)
    manufacturing_date = ANCHOR_DATE - timedelta(days=rng.randint(60, 700))
    shelf_life_days = rng.randint(365, 1095)
    expiry_date = manufacturing_date + timedelta(days=shelf_life_days)
    reorder_level = rng.randint(50, 150)
    maximum_stock = reorder_level + rng.randint(150, 650)
    current_stock = rng.randint(reorder_level + 10, maximum_stock - 10)
    unit_price = round(rng.uniform(0.5, 500.0), 2)
    return {
        "Batch_ID": f"BATCH-{idx:04d}",
        "Medicine_Name": name,
        "Category": category,
        "Manufacturer": rng.choice(MANUFACTURERS),
        "Manufacturing_Date": _fmt(manufacturing_date),
        "Expiry_Date": _fmt(expiry_date),
        "Current_Stock": current_stock,
        "Reorder_Level": reorder_level,
        "Maximum_Stock": maximum_stock,
        "Unit_Price": unit_price,
        "Warehouse": rng.choice(WAREHOUSES),
        "Critical_Medicine": rng.choice(CRITICAL_CHOICES_WEIGHTED),
    }


def generate_rows() -> list[dict]:
    rng = _rng()
    rows: list[dict] = []
    idx = 1

    def next_idx() -> int:
        nonlocal idx
        idx += 1
        return idx - 1

    # 20 expired batches
    for _ in range(20):
        row = _base_batch(rng, next_idx())
        expired_date = ANCHOR_DATE - timedelta(days=rng.randint(1, 900))
        row["Expiry_Date"] = _fmt(expired_date)
        row["Manufacturing_Date"] = _fmt(expired_date - timedelta(days=rng.randint(365, 1095)))
        rows.append(row)

    # 20 batches expiring within 30 days
    for _ in range(20):
        row = _base_batch(rng, next_idx())
        soon_date = ANCHOR_DATE + timedelta(days=rng.randint(0, 30))
        row["Expiry_Date"] = _fmt(soon_date)
        row["Manufacturing_Date"] = _fmt(ANCHOR_DATE - timedelta(days=rng.randint(365, 1000)))
        rows.append(row)

    # 20 low stock batches
    for _ in range(20):
        row = _base_batch(rng, next_idx())
        row["Current_Stock"] = max(0, row["Reorder_Level"] - rng.randint(5, 50))
        rows.append(row)

    # 20 overstock batches
    for _ in range(20):
        row = _base_batch(rng, next_idx())
        row["Current_Stock"] = row["Maximum_Stock"] + rng.randint(10, 200)
        rows.append(row)

    # 15 rows with a missing value in one field
    for i in range(15):
        row = _base_batch(rng, next_idx())
        col = MISSING_TARGET_COLUMNS[i % len(MISSING_TARGET_COLUMNS)]
        row[col] = ""
        rows.append(row)

    # 10 rows with invalid/malformed dates
    for i in range(10):
        row = _base_batch(rng, next_idx())
        if i % 2 == 0:
            row["Expiry_Date"] = INVALID_DATE_STRINGS[i % len(INVALID_DATE_STRINGS)]
        else:
            manufacturing_date = ANCHOR_DATE + timedelta(days=rng.randint(30, 200))
            expiry_date = ANCHOR_DATE - timedelta(days=rng.randint(1, 60))
            row["Manufacturing_Date"] = _fmt(manufacturing_date)
            row["Expiry_Date"] = _fmt(expiry_date)
        rows.append(row)

    # 10 rows with negative stock
    for _ in range(10):
        row = _base_batch(rng, next_idx())
        row["Current_Stock"] = -rng.randint(1, 60)
        rows.append(row)

    # remaining unique rows are clean baseline batches
    unique_target = 195
    while len(rows) < unique_target:
        rows.append(_base_batch(rng, next_idx()))

    # 5 exact duplicate records (accidental double-entry of the same batch)
    dup_source_rows = rng.sample(rows, 5)
    for src in dup_source_rows:
        rows.append(dict(src))

    rng.shuffle(rows)
    return rows


def main() -> None:
    rows = generate_rows()
    df = pd.DataFrame(rows, columns=COLUMNS)
    assert len(df) == 200, f"expected 200 rows, got {len(df)}"

    out_path = Path(__file__).resolve().parent.parent / "data" / "pharma_inventory.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")


if __name__ == "__main__":
    main()
