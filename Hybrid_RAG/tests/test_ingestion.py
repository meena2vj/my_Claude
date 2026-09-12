import fitz
import pytest

from src.ingestion.chunking import chunk_pages
from src.ingestion.pdf_processor import PageRecord, PDFExtractionError, extract_pdf_pages, process_uploaded_pdfs


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


def test_process_uploaded_pdfs_multi_pdf_preserves_both_sources():
    doc_a = FakeUploadedFile("a.pdf", make_pdf_bytes(["Content from document A"]))
    doc_b = FakeUploadedFile("b.pdf", make_pdf_bytes(["Content from document B"]))

    records, errors = process_uploaded_pdfs([doc_a, doc_b])

    assert errors == []
    assert {r.file_name for r in records} == {"a.pdf", "b.pdf"}


def test_chunk_pages_respects_chunk_size_and_preserves_metadata():
    text = "abcdefghij" * 20  # 200 chars
    page = PageRecord(file_name="doc.pdf", page_number=3, page_text=text, is_empty=False)

    chunks = chunk_pages([page], chunk_size=50, chunk_overlap=10)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 50
        assert chunk.source_file == "doc.pdf"
        assert chunk.page_number == 3
        assert chunk.is_suspicious is False


def test_chunk_pages_assigns_unique_sequential_ids_across_pages():
    page1 = PageRecord(file_name="a.pdf", page_number=1, page_text="x" * 300, is_empty=False)
    page2 = PageRecord(file_name="b.pdf", page_number=1, page_text="y" * 300, is_empty=False)

    chunks = chunk_pages([page1, page2], chunk_size=100, chunk_overlap=0)

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_chunk_pages_skips_empty_pages():
    page = PageRecord(file_name="doc.pdf", page_number=1, page_text="", is_empty=True)
    assert chunk_pages([page]) == []
