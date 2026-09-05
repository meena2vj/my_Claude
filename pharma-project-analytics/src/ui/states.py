"""Professional loading / empty / invalid-file / success / error states.

Per `.claude/skills/professional-ui/SKILL.md` ("Error & Empty States"):
calm, specific, actionable messages - never a raw stack trace or a blank
page.
"""

from __future__ import annotations

import streamlit as st

LOADING_MESSAGE = "Processing inventory data..."

UPLOAD_HELP_MESSAGE = (
    "Upload a CSV or Excel file with the required inventory columns "
    "(Batch_ID, Medicine_Name, Category, Manufacturer, Manufacturing_Date, "
    "Expiry_Date, Current_Stock, Reorder_Level, Maximum_Stock, Unit_Price, "
    "Warehouse, Critical_Medicine) to analyse your own data. "
    "Until then, the dashboard shows the bundled synthetic sample dataset."
)

GENERIC_ERROR_MESSAGE = (
    "Something went wrong while processing this data. Please check the file "
    "and try again. If the problem persists, try re-uploading a smaller or "
    "simpler file."
)


def render_empty_data_state(context: str = "the current selection") -> None:
    """No rows to show for `context` (e.g. an empty file, or filters that
    exclude every row). Never render a blank chart in this situation.
    """
    st.info(
        f"No data available for {context}. "
        "Try uploading a file with rows, or adjust/reset the filters in the sidebar."
    )


def render_invalid_file_state(message: str) -> None:
    """A specific, actionable message for a rejected upload. `message`
    should already be the DataValidationError's text.
    """
    st.error(f"This file could not be used: {message}")


def render_success_state(filename: str, row_count: int, processed_at: str) -> None:
    st.success(
        f"Loaded **{filename}** — {row_count:,} row(s) — processed {processed_at}."
    )


def render_unexpected_error_state() -> None:
    """User-friendly fallback for any exception not already handled as an
    invalid-file case. The real exception should be logged server-side by
    the caller, never shown to the user.
    """
    st.error(GENERIC_ERROR_MESSAGE)
