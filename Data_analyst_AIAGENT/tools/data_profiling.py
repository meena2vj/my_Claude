"""Deterministic data-quality profiling: pure Pandas/NumPy, no LLM."""

import numpy as np
import pandas as pd

from graph.state import ColumnIssue, QualityReport


def _percentage(count: int, total: int) -> float:
    return round(100 * count / total, 2) if total else 0.0


def _outlier_bounds(series: pd.Series) -> tuple[float, float]:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def profile_dataframe(df: pd.DataFrame) -> QualityReport:
    row_count, column_count = df.shape

    missing_by_column = [
        ColumnIssue(column=col, count=int(n), percentage=_percentage(int(n), row_count))
        for col, n in df.isna().sum().items()
        if n > 0
    ]

    duplicate_row_count = int(df.duplicated().sum())
    duplicate_row_percentage = _percentage(duplicate_row_count, row_count)

    numeric_columns = df.select_dtypes(include="number").columns.tolist()
    categorical_columns = [c for c in df.columns if c not in numeric_columns]

    outliers_by_column: list[ColumnIssue] = []
    for col in numeric_columns:
        series = df[col].dropna()
        if len(series) < 4:
            continue
        low, high = _outlier_bounds(series)
        n_out = int(((series < low) | (series > high)).sum())
        if n_out:
            outliers_by_column.append(
                ColumnIssue(column=col, count=n_out, percentage=_percentage(n_out, row_count))
            )

    unique_counts = {col: int(df[col].nunique(dropna=True)) for col in df.columns}

    invalid_value_columns: list[ColumnIssue] = []
    for col in df.columns:
        if col in numeric_columns:
            n_invalid = int(np.isinf(df[col].dropna()).sum())
        else:
            n_invalid = int((df[col].astype(str).str.strip() == "").sum())
        if n_invalid:
            invalid_value_columns.append(
                ColumnIssue(column=col, count=n_invalid, percentage=_percentage(n_invalid, row_count))
            )

    constant_columns = [col for col in df.columns if df[col].nunique(dropna=True) <= 1]

    descriptive_stats: dict[str, dict[str, float]] = {}
    for col in numeric_columns:
        series = df[col].dropna()
        if series.empty:
            continue
        descriptive_stats[col] = {
            "mean": float(series.mean()),
            "std": float(series.std()) if len(series) > 1 else 0.0,
            "min": float(series.min()),
            "max": float(series.max()),
            "median": float(series.median()),
        }

    return QualityReport(
        row_count=row_count,
        column_count=column_count,
        missing_by_column=missing_by_column,
        duplicate_row_count=duplicate_row_count,
        duplicate_row_percentage=duplicate_row_percentage,
        outliers_by_column=outliers_by_column,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        unique_counts=unique_counts,
        invalid_value_columns=invalid_value_columns,
        constant_columns=constant_columns,
        descriptive_stats=descriptive_stats,
    )
