import numpy as np

import services.rag_business_context as rag
from graph.state import ContextChunk


def _make_chunk(chunk_id, text):
    return ContextChunk(
        chunk_id=chunk_id, doc_id="d1", filename="f.txt", page=1, text=text, token_count=len(text.split())
    )


def test_retrieve_returns_most_similar_chunks(mocker):
    chunks = [
        _make_chunk("c1", "revenue grew"),
        _make_chunk("c2", "unrelated text"),
        _make_chunk("c3", "revenue increased"),
    ]

    def fake_embed(texts):
        return np.array(
            [[1.0, 0.0] if "revenue" in t else [0.0, 1.0] for t in texts], dtype="float32"
        )

    mocker.patch.object(rag, "embed_texts", side_effect=fake_embed)

    results = rag.retrieve(chunks, "revenue trend", top_k=2)
    assert {r.chunk_id for r in results} == {"c1", "c3"}


def test_retrieve_empty_chunks_returns_empty():
    assert rag.retrieve([], "anything") == []


def test_ingest_document_txt_creates_chunks():
    doc, chunks = rag.ingest_document("notes.txt", b"Some business context. " * 50, ".txt")
    assert doc.filename == "notes.txt"
    assert len(chunks) >= 1
    assert all(c.doc_id == doc.doc_id for c in chunks)
