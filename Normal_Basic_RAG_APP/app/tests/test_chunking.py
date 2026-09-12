from chunking import chunk_pages
from pdf_processor import PageRecord


def test_chunk_pages_respects_chunk_size_and_preserves_metadata():
    text = "abcdefghij" * 20  # 200 chars
    page = PageRecord(file_name="doc.pdf", page_number=3, page_text=text, is_empty=False)

    chunks = chunk_pages([page], chunk_size=50, chunk_overlap=10)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 50
        assert chunk.source_file == "doc.pdf"
        assert chunk.page_number == 3
        assert chunk.token_count == len(chunk.text.split())


def test_chunk_pages_overlap_between_consecutive_chunks():
    text = "abcdefghij" * 20
    page = PageRecord(file_name="doc.pdf", page_number=1, page_text=text, is_empty=False)

    chunks = chunk_pages([page], chunk_size=50, chunk_overlap=10)

    assert len(chunks) >= 2
    tail_of_first = chunks[0].text[-10:]
    head_of_second = chunks[1].text[:10]
    assert tail_of_first == head_of_second


def test_chunk_pages_skips_empty_pages():
    page = PageRecord(file_name="doc.pdf", page_number=1, page_text="", is_empty=True)

    assert chunk_pages([page]) == []


def test_chunk_pages_assigns_unique_sequential_ids_across_pages():
    page1 = PageRecord(file_name="a.pdf", page_number=1, page_text="x" * 300, is_empty=False)
    page2 = PageRecord(file_name="b.pdf", page_number=1, page_text="y" * 300, is_empty=False)

    chunks = chunk_pages([page1, page2], chunk_size=100, chunk_overlap=0)

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert any(chunk.source_file == "a.pdf" for chunk in chunks)
    assert any(chunk.source_file == "b.pdf" for chunk in chunks)


def test_chunk_pages_empty_input_returns_empty_list():
    assert chunk_pages([]) == []
