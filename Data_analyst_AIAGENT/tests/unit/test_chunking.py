from services.chunking import chunk_text


def test_chunk_text_splits_long_text():
    text = "word " * 500
    chunks = chunk_text(text)
    assert len(chunks) > 1


def test_chunk_text_empty_returns_no_chunks():
    assert chunk_text("   ") == []
