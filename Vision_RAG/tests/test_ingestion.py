import io

import fitz
import pytest
from PIL import Image

from utils import file_loader
from utils.file_loader import FileValidationError, process_uploaded_files, validate_file


class FakeUploadedFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def _png_bytes(size=(20, 20), color=(255, 255, 255)) -> bytes:
    image = Image.new("RGB", size, color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes(page_count: int = 1) -> bytes:
    document = fitz.open()
    for _ in range(page_count):
        document.new_page()
    data = document.tobytes()
    document.close()
    return data


def test_validate_file_rejects_bad_extension():
    with pytest.raises(FileValidationError):
        validate_file("doc.txt", b"hello")


def test_validate_file_rejects_empty():
    with pytest.raises(FileValidationError):
        validate_file("doc.png", b"")


def test_validate_file_rejects_oversized(monkeypatch):
    monkeypatch.setattr(file_loader, "MAX_UPLOAD_FILE_SIZE_MB", 0)
    with pytest.raises(FileValidationError):
        validate_file("doc.png", _png_bytes())


def test_process_uploaded_files_image_uses_ocr(monkeypatch):
    monkeypatch.setattr(
        file_loader, "extract_text_from_image_bytes", lambda data, reader=None: ("Invoice total 42", 0.9)
    )
    uploaded = FakeUploadedFile("invoice.png", _png_bytes())

    documents, pages, errors = process_uploaded_files([uploaded])

    assert not errors
    assert len(documents) == 1
    assert documents[0].source_type == "image"
    assert len(pages) == 1
    assert pages[0].page_text == "Invoice total 42"
    assert pages[0].ocr_confidence == 0.9


def test_process_uploaded_files_pdf_renders_and_ocrs_each_page(monkeypatch):
    monkeypatch.setattr(
        file_loader, "extract_text_from_image_bytes", lambda data, reader=None: ("Page text", 0.8)
    )
    uploaded = FakeUploadedFile("report.pdf", _pdf_bytes(page_count=2))

    documents, pages, errors = process_uploaded_files([uploaded])

    assert not errors
    assert documents[0].page_count == 2
    assert len(pages) == 2
    assert all(p.source_type == "pdf_page" for p in pages)


def test_process_uploaded_files_flags_low_ocr_confidence(monkeypatch):
    monkeypatch.setattr(
        file_loader, "extract_text_from_image_bytes", lambda data, reader=None: ("j9$ x2q", 0.1)
    )
    uploaded = FakeUploadedFile("scan.png", _png_bytes())

    documents, pages, errors = process_uploaded_files([uploaded])

    assert any("low OCR confidence" in e for e in errors)


def test_process_uploaded_files_skips_bad_file_without_crashing(monkeypatch):
    monkeypatch.setattr(
        file_loader, "extract_text_from_image_bytes", lambda data, reader=None: ("ok", 0.9)
    )
    good = FakeUploadedFile("good.png", _png_bytes())
    bad = FakeUploadedFile("bad.exe", b"not-an-image")

    documents, pages, errors = process_uploaded_files([good, bad])

    assert len(documents) == 1
    assert any("unsupported extension" in e for e in errors)
