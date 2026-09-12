"""PDF text extraction using PyMuPDF (fitz) only.

Extracts file name, page number, and page text for every page, preserving
source metadata for citations. A single corrupt/unreadable PDF never crashes
the batch, and empty/scanned (no extractable text) pages are flagged rather
than raising.
"""

from dataclasses import dataclass

import fitz  # PyMuPDF

from utils import clean_text


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or read by PyMuPDF."""


@dataclass
class PageRecord:
    file_name: str
    page_number: int  # 1-indexed
    page_text: str
    is_empty: bool


def extract_pdf_pages(file_bytes: bytes, file_name: str) -> list[PageRecord]:
    """Extract per-page text from a single PDF's raw bytes.

    Raises PDFExtractionError if the file cannot be opened as a PDF.
    """
    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFExtractionError(f"Could not open '{file_name}' as a PDF: {exc}") from exc

    records: list[PageRecord] = []
    try:
        for page_index in range(document.page_count):
            try:
                page = document.load_page(page_index)
                raw_text = page.get_text("text") or ""
            except Exception:
                raw_text = ""
            text = clean_text(raw_text)
            records.append(
                PageRecord(
                    file_name=file_name,
                    page_number=page_index + 1,
                    page_text=text,
                    is_empty=len(text) == 0,
                )
            )
    finally:
        document.close()

    return records


def process_uploaded_pdfs(
    uploaded_files: list,
) -> tuple[list[PageRecord], list[str]]:
    """Process multiple uploaded PDFs, skipping any that fail.

    `uploaded_files` items must expose `.name` and `.getvalue()`/`.read()`
    (Streamlit's UploadedFile satisfies this).

    Returns (all_page_records, error_messages) — one entry in error_messages
    per file that failed, so the caller can surface friendly warnings without
    losing the successfully processed files.
    """
    all_records: list[PageRecord] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        file_name = getattr(uploaded_file, "name", "unknown.pdf")
        try:
            file_bytes = (
                uploaded_file.getvalue()
                if hasattr(uploaded_file, "getvalue")
                else uploaded_file.read()
            )
            if not file_bytes:
                errors.append(f"'{file_name}' is empty and was skipped.")
                continue
            records = extract_pdf_pages(file_bytes, file_name)
            if not records:
                errors.append(f"'{file_name}' has no pages and was skipped.")
                continue
            all_records.extend(records)
        except PDFExtractionError as exc:
            errors.append(str(exc))
        except Exception as exc:  # never let one bad file crash the batch
            errors.append(f"Unexpected error processing '{file_name}': {exc}")

    return all_records, errors
