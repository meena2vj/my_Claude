"""Extract per-page text from a PDF using PyMuPDF, in-memory (no temp files)."""

import fitz


def extract_pages(raw_bytes: bytes) -> list[tuple[int, str]]:
    doc = fitz.open(stream=raw_bytes, filetype="pdf")
    try:
        return [(i + 1, page.get_text()) for i, page in enumerate(doc)]
    finally:
        doc.close()
