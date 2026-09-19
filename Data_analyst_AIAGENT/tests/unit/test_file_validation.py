import io

import pytest

from tools.file_validation import (
    FileValidationError,
    load_dataframe,
    sanitize_filename,
    validate_and_save,
)


class FakeUploadedFile:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def test_sanitize_filename_strips_unsafe_characters():
    safe = sanitize_filename("weird name!.csv")
    assert safe == "weird_name_.csv"


def test_sanitize_filename_is_safe_for_traversal_attempt():
    safe = sanitize_filename("../../../etc/passwd")
    assert "/" not in safe
    assert ".." not in safe


def test_validate_and_save_rejects_disallowed_extension(tmp_path):
    f = FakeUploadedFile("malware.exe", b"data")
    with pytest.raises(FileValidationError):
        validate_and_save(f, dest_dir=tmp_path)


def test_validate_and_save_rejects_empty_file(tmp_path):
    f = FakeUploadedFile("data.csv", b"")
    with pytest.raises(FileValidationError):
        validate_and_save(f, dest_dir=tmp_path)


def test_validate_and_save_rejects_oversized_file(tmp_path):
    f = FakeUploadedFile("data.csv", b"x" * 1024)
    with pytest.raises(FileValidationError):
        validate_and_save(f, dest_dir=tmp_path, max_size_mb=0)


def test_validate_and_save_writes_sanitized_file(tmp_path):
    f = FakeUploadedFile("../weird name!.csv", b"a,b\n1,2\n")
    validated = validate_and_save(f, dest_dir=tmp_path)
    assert validated.path.exists()
    assert validated.extension == ".csv"


def test_load_dataframe_parses_csv(tmp_path):
    f = FakeUploadedFile("sales.csv", b"a,b\n1,2\n3,4\n")
    validated = validate_and_save(f, dest_dir=tmp_path)
    df, meta = load_dataframe(validated)
    assert list(df.columns) == ["a", "b"]
    assert meta.rows == 2
    assert meta.columns == 2


def test_load_dataframe_rejects_empty_csv(tmp_path):
    f = FakeUploadedFile("empty.csv", b"a,b\n")
    validated = validate_and_save(f, dest_dir=tmp_path)
    with pytest.raises(FileValidationError):
        load_dataframe(validated)
