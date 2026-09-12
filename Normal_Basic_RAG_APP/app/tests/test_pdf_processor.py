import fitz
import pytest

from pdf_processor import PDFExtractionError, extract_pdf_pages, process_uploaded_pdfs


def make_pdf_bytes(pages_text: list[str]) -> bytes:
    document = fitz.open()
    for text in pages_text:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


class FakeUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_extract_pdf_pages_preserves_metadata():
    data = make_pdf_bytes(["Hello world", "Second page text"])
    records = extract_pdf_pages(data, "sample.pdf")

    assert len(records) == 2
    assert records[0].file_name == "sample.pdf"
    assert records[0].page_number == 1
    assert "Hello world" in records[0].page_text
    assert records[1].page_number == 2
    assert "Second page text" in records[1].page_text


def test_extract_pdf_pages_flags_empty_page():
    data = make_pdf_bytes([""])
    records = extract_pdf_pages(data, "empty.pdf")

    assert len(records) == 1
    assert records[0].is_empty is True
    assert records[0].page_text == ""


def test_extract_pdf_pages_raises_on_invalid_pdf():
    with pytest.raises(PDFExtractionError):
        extract_pdf_pages(b"not a real pdf", "bad.pdf")


def test_process_uploaded_pdfs_skips_bad_file_without_crashing():
    good = FakeUploadedFile("good.pdf", make_pdf_bytes(["Some real content"]))
    bad = FakeUploadedFile("bad.pdf", b"garbage-not-a-pdf")

    records, errors = process_uploaded_pdfs([good, bad])

    assert len(records) == 1
    assert records[0].file_name == "good.pdf"
    assert len(errors) == 1
    assert "bad.pdf" in errors[0]


def test_process_uploaded_pdfs_skips_empty_file():
    empty = FakeUploadedFile("empty.pdf", b"")

    records, errors = process_uploaded_pdfs([empty])

    assert records == []
    assert len(errors) == 1
    assert "empty.pdf" in errors[0]
