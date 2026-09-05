"""Pure filter-application logic for the dashboard sidebar filters.

Kept separate from `src/ui/sidebar.py` per CLAUDE.md ("No business logic
inside Streamlit callback/render functions") so filtering behaviour is
unit-testable without Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class FilterSelection:
    """One field per sidebar filter. An empty list means "no restriction"
    on that field - all values pass.
    """

    medicines: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    warehouses: list[str] = field(default_factory=list)
    expiry_statuses: list[str] = field(default_factory=list)
    stock_statuses: list[str] = field(default_factory=list)
    risk_levels: list[str] = field(default_factory=list)


_FIELD_TO_COLUMN = {
    "medicines": "Medicine_Name",
    "categories": "Category",
    "warehouses": "Warehouse",
    "expiry_statuses": "Expiry_Status",
    "stock_statuses": "Stock_Status",
    "risk_levels": "Risk_Level",
}


def apply_filters(df: pd.DataFrame, selection: FilterSelection) -> pd.DataFrame:
    """Return the subset of `df` matching every non-empty filter field
    (AND across fields). A field left empty imposes no restriction.
    """
    mask = pd.Series(True, index=df.index)
    for field_name, column in _FIELD_TO_COLUMN.items():
        values = getattr(selection, field_name)
        if values:
            mask &= df[column].isin(values)
    return df[mask]
