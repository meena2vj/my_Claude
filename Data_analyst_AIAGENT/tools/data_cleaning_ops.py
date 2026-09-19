"""Cleaning-plan generation and execution.

`build_default_plan` is the deterministic fallback the cleaning agent uses
when no LLM is configured (or as the basis it hands the LLM to narrate).
`execute_plan` is the only function that materializes `clean_data` -- it
always operates on a copy, `raw_data` is never mutated. Non-destructive
actions (flags) never drop or alter values; only `drop_duplicates` and
`impute_missing` change the frame, and both are logged with row counts.
"""

import uuid

import pandas as pd

from graph.state import CleaningAction, QualityReport


def build_default_plan(df: pd.DataFrame, quality_report: QualityReport) -> list[CleaningAction]:
    rows = len(df)
    actions: list[CleaningAction] = []

    for issue in quality_report.missing_by_column:
        is_numeric = issue.column in quality_report.numeric_columns
        method = "median imputation" if is_numeric else "mode imputation"
        actions.append(
            CleaningAction(
                action_id=str(uuid.uuid4()),
                action_type="impute_missing",
                column=issue.column,
                description=f"Fill {issue.count} missing value(s) in '{issue.column}' using {method}.",
                destructive=False,
                rows_before=rows,
                rows_after=rows,
            )
        )

    if quality_report.duplicate_row_count:
        actions.append(
            CleaningAction(
                action_id=str(uuid.uuid4()),
                action_type="drop_duplicates",
                column=None,
                description=f"Remove {quality_report.duplicate_row_count} duplicate row(s).",
                destructive=True,
                rows_before=rows,
                rows_after=rows - quality_report.duplicate_row_count,
            )
        )

    for issue in quality_report.outliers_by_column:
        actions.append(
            CleaningAction(
                action_id=str(uuid.uuid4()),
                action_type="flag_outliers",
                column=issue.column,
                description=(
                    f"Flag {issue.count} outlier value(s) in '{issue.column}' "
                    "(IQR method) without removing them."
                ),
                destructive=False,
                rows_before=rows,
                rows_after=rows,
            )
        )

    for col in quality_report.constant_columns:
        actions.append(
            CleaningAction(
                action_id=str(uuid.uuid4()),
                action_type="flag_constant_column",
                column=col,
                description=f"Column '{col}' is constant across all rows; flagged for review, not removed.",
                destructive=False,
                rows_before=rows,
                rows_after=rows,
            )
        )

    for issue in quality_report.invalid_value_columns:
        actions.append(
            CleaningAction(
                action_id=str(uuid.uuid4()),
                action_type="flag_invalid_values",
                column=issue.column,
                description=f"Flag {issue.count} invalid/blank value(s) in '{issue.column}' for review.",
                destructive=False,
                rows_before=rows,
                rows_after=rows,
            )
        )

    return actions


def execute_plan(
    df: pd.DataFrame, plan: list[CleaningAction]
) -> tuple[pd.DataFrame, list[CleaningAction]]:
    clean_df = df.copy(deep=True)
    log: list[CleaningAction] = []

    for action in plan:
        rows_before = len(clean_df)
        if action.action_type == "impute_missing" and action.column in clean_df.columns:
            col = action.column
            if pd.api.types.is_numeric_dtype(clean_df[col]):
                fill_value = clean_df[col].median()
            else:
                mode = clean_df[col].mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else ""
            clean_df[col] = clean_df[col].fillna(fill_value)
        elif action.action_type == "drop_duplicates":
            clean_df = clean_df.drop_duplicates().reset_index(drop=True)
        # flag_* actions are informational only -- no mutation.

        rows_after = len(clean_df)
        log.append(
            action.model_copy(update={"rows_before": rows_before, "rows_after": rows_after, "executed": True})
        )

    return clean_df, log
