"""Ingestion: validate uploads, rasterize PDFs to page images, OCR everything.

Every input — a plain image or a PDF page — ends up going through the same
OCR path. PDFs are rendered page-by-page to images with PyMuPDF (fitz) first,
which is what CLAUDE.md's Skill 1 calls for ("Use PyMuPDF for PDF and
page-level extraction when relevant") while keeping one unified vision
pipeline instead of a separate PDF-text-layer code path.
"""

import io
import uuid

import fitz  # PyMuPDF
from PIL import Image

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_FILE_SIZE_MB, OCR_MIN_CONFIDENCE, PDF_RENDER_DPI
from utils.data_models import DocumentRecord, PageRecord
from utils.helpers import clean_text
from utils.ocr_utils import OCRExtractionError, extract_text_from_image_bytes


class FileValidationError(Exception):
    """Raised when an uploaded file fails validation before any processing."""


def validate_file(file_name: str, file_bytes: bytes) -> None:
    lower_name = file_name.lower()
    if not any(lower_name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise FileValidationError(
            f"'{file_name}' has an unsupported extension. Allowed: {', '.join(ALLOWED_EXTENSIONS)}."
        )
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_FILE_SIZE_MB:
        raise FileValidationError(
            f"'{file_name}' is {size_mb:.1f} MB, exceeding the {MAX_UPLOAD_FILE_SIZE_MB} MB limit."
        )
    if not file_bytes:
        raise FileValidationError(f"'{file_name}' is empty.")


def _render_pdf_pages_to_images(file_bytes: bytes, file_name: str, dpi: int = PDF_RENDER_DPI) -> list[bytes]:
    try:
        document = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise FileValidationError(f"Could not open '{file_name}' as a PDF: {exc}") from exc

    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    page_images: list[bytes] = []
    try:
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            page_images.append(buffer.getvalue())
    finally:
        document.close()

    return page_images


def process_uploaded_files(uploaded_files: list) -> tuple[list[DocumentRecord], list[PageRecord], list[str]]:
    """Process multiple uploaded images/PDFs, skipping any that fail.

    `uploaded_files` items must expose `.name` and `.getvalue()`/`.read()`
    (Streamlit's UploadedFile satisfies this).

    Returns (documents, pages, error_messages) — one entry in error_messages
    per file that failed, so the caller can surface friendly warnings without
    losing the successfully processed files.
    """
    documents: list[DocumentRecord] = []
    all_pages: list[PageRecord] = []
    errors: list[str] = []

    for uploaded_file in uploaded_files:
        file_name = getattr(uploaded_file, "name", "unknown")
        try:
            file_bytes = (
                uploaded_file.getvalue() if hasattr(uploaded_file, "getvalue") else uploaded_file.read()
            )
            validate_file(file_name, file_bytes)

            is_pdf = file_name.lower().endswith(".pdf")
            if is_pdf:
                page_images = _render_pdf_pages_to_images(file_bytes, file_name)
                source_type = "pdf_page"
            else:
                page_images = [file_bytes]
                source_type = "image"

            document_id = str(uuid.uuid4())[:8]
            pages: list[PageRecord] = []
            for page_index, image_bytes in enumerate(page_images, start=1):
                try:
                    text, confidence = extract_text_from_image_bytes(image_bytes)
                except OCRExtractionError as exc:
                    errors.append(f"OCR failed on '{file_name}' page {page_index}: {exc}")
                    text, confidence = "", 0.0

                cleaned = clean_text(text)
                pages.append(
                    PageRecord(
                        document_id=document_id,
                        file_name=file_name,
                        page_number=page_index,
                        page_text=cleaned,
                        is_empty=len(cleaned) == 0,
                        ocr_confidence=confidence,
                        source_type=source_type,
                    )
                )

            if not pages:
                errors.append(f"'{file_name}' produced no pages and was skipped.")
                continue

            low_confidence_pages = sum(1 for p in pages if 0 < p.ocr_confidence < OCR_MIN_CONFIDENCE)
            if low_confidence_pages:
                errors.append(
                    f"'{file_name}' has {low_confidence_pages} page(s) with low OCR confidence "
                    "(noisy scan or low contrast) — text may be unreliable."
                )

            documents.append(
                DocumentRecord(
                    document_id=document_id,
                    file_name=file_name,
                    source_type=source_type,
                    page_count=len(pages),
                )
            )
            all_pages.extend(pages)
        except FileValidationError as exc:
            errors.append(str(exc))
        except Exception as exc:  # never let one bad file crash the batch
            errors.append(f"Unexpected error processing '{file_name}': {exc}")

    return documents, all_pages, errors
