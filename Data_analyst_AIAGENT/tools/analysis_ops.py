"""Deterministic analysis primitives.

These are the only functions in the codebase allowed to produce numbers for
the analyst. An LLM may pick *which* column/grouping to use and may write a
narrative, but it never computes a figure -- `validate_narrative_against_result`
is the enforcement mechanism that catches an LLM stating a number that isn't
actually in the executed result.
"""

import re

import pandas as pd


def match_column(term: str, columns: list[str]) -> str | None:
    """Best-effort case-insensitive match between a KPI/question term and an
    actual column name (exact match first, then substring)."""
    term_lower = term.lower().strip()
    if not term_lower:
        return None
    for col in columns:
        if col.lower() == term_lower:
            return col
    for col in columns:
        if col.lower() in term_lower or term_lower in col.lower():
            return col
    return None


def aggregate_by_group(
    df: pd.DataFrame, value_col: str, group_col: str | None, agg: str = "sum"
) -> pd.DataFrame:
    if group_col and group_col in df.columns and group_col != value_col:
        result = df.groupby(group_col, dropna=False)[value_col].agg(agg).reset_index()
        result.columns = [group_col, value_col]
        return result.sort_values(value_col, ascending=False).reset_index(drop=True)
    return pd.DataFrame({value_col: [df[value_col].agg(agg)]})


_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def extract_numbers(text: str) -> set[float]:
    found = set()
    for token in _NUMBER_PATTERN.findall(text):
        cleaned = token.replace(",", "")
        try:
            found.add(float(cleaned))
        except ValueError:
            continue
    return found


def validate_narrative_against_result(
    narrative: str, result_table: pd.DataFrame, tolerance: float = 0.01
) -> list[str]:
    """Return one problem string per number in `narrative` that cannot be
    traced (within tolerance) to any numeric value in `result_table`. An
    empty list means the narrative is validated."""
    narrative_numbers = extract_numbers(narrative)
    if not narrative_numbers:
        return []

    table_numbers: set[float] = set()
    for col in result_table.select_dtypes(include="number").columns:
        table_numbers.update(float(v) for v in result_table[col].dropna().tolist())

    problems = []
    for n in narrative_numbers:
        if not any(abs(n - t) <= tolerance * max(abs(t), 1.0) for t in table_numbers):
            problems.append(f"Could not trace the number {n} in the narrative to the result table.")
    return problems
