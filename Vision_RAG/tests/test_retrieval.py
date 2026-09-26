import numpy as np
import pytest

from utils import faiss_store
from utils.bm25_index import BM25IndexError, build_bm25_index, search_bm25
from utils.chunking import chunk_pages
from utils.data_models import ChunkRecord, PageRecord
from utils.faiss_store import VectorStoreError, build_dense_index, search_dense
from utils.fusion import reciprocal_rank_fusion, retrieve


def _page(text: str, page_number: int = 1, file_name: str = "doc.png") -> PageRecord:
    return PageRecord(
        document_id="d1", file_name=file_name, page_number=page_number,
        page_text=text, is_empty=len(text) == 0, ocr_confidence=0.9, source_type="image",
    )


def _chunk(chunk_id: str, text: str, source_file: str = "doc.png") -> ChunkRecord:
    return ChunkRecord(chunk_id=chunk_id, source_file=source_file, page_number=1, text=text, ocr_confidence=0.9)


def test_chunk_pages_splits_long_page_and_skips_empty():
    pages = [_page("word " * 400), _page("", page_number=2)]
    chunks = chunk_pages(pages, chunk_size=800, chunk_overlap=0)
    assert len(chunks) >= 2
    assert all(c.source_file == "doc.png" for c in chunks)


def test_build_bm25_index_rejects_empty():
    with pytest.raises(BM25IndexError):
        build_bm25_index([])


def test_search_bm25_ranks_matching_chunk_first():
    # BM25's idf term is ~0 when a term appears in exactly half of a 2-doc
    # corpus, so a 3rd unrelated doc is needed for a meaningful non-zero score.
    chunks = [
        _chunk("chunk_1", "the invoice due date is march 3rd"),
        _chunk("chunk_2", "unrelated text about weather patterns"),
        _chunk("chunk_3", "another unrelated passage about gardening tips"),
    ]
    store = build_bm25_index(chunks)
    results = search_bm25("invoice due date", store, top_k=2)
    assert results
    assert results[0].chunk_id == "chunk_1"


def test_search_bm25_empty_query_returns_nothing():
    chunks = [_chunk("chunk_1", "some text")]
    store = build_bm25_index(chunks)
    assert search_bm25("", store, top_k=5) == []


def test_build_dense_index_rejects_mismatched_counts():
    chunks = [_chunk("chunk_1", "a")]
    embeddings = np.zeros((2, 4), dtype="float32")
    with pytest.raises(VectorStoreError):
        build_dense_index(embeddings, chunks)


def test_search_dense_returns_closest_match(monkeypatch):
    chunks = [_chunk("chunk_1", "cat"), _chunk("chunk_2", "dog")]

    def fake_embed(texts, model=None, batch_size=32):
        vectors = []
        for t in texts:
            vectors.append([1.0, 0.0] if "cat" in t else [0.0, 1.0])
        return np.array(vectors, dtype="float32")

    monkeypatch.setattr(faiss_store, "embed_texts", fake_embed)
    store = build_dense_index(fake_embed(["cat", "dog"]), chunks)
    results = search_dense("cat", store, top_k=1)
    assert results[0].chunk_id == "chunk_1"


def test_reciprocal_rank_fusion_merges_overlapping_and_disjoint_hits():
    from utils.data_models import RankedChunk

    dense = [RankedChunk(chunk_id="a", source_file="f", page_number=1, text="a", score=0.9, rank=1)]
    sparse = [
        RankedChunk(chunk_id="a", source_file="f", page_number=1, text="a", score=5.0, rank=2),
        RankedChunk(chunk_id="b", source_file="f", page_number=2, text="b", score=3.0, rank=1),
    ]
    fused = reciprocal_rank_fusion(dense, sparse, k=60)
    fused_ids = [c.chunk_id for c in fused]
    assert "a" in fused_ids and "b" in fused_ids
    # "a" appears in both lists so its fused score must exceed "b" (single-list only)
    a_score = next(c.fused_score for c in fused if c.chunk_id == "a")
    b_score = next(c.fused_score for c in fused if c.chunk_id == "b")
    assert a_score > b_score


def test_retrieve_rejects_unknown_mode():
    with pytest.raises(ValueError):
        retrieve("q", "unknown", None, None, top_k=5)


def test_retrieve_dense_mode_with_no_store_returns_empty():
    assert retrieve("q", "dense", None, None, top_k=5) == []
