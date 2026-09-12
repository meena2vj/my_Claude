from src.hybrid.fusion import reciprocal_rank_fusion, retrieve
from src.evaluation.metrics import recall_at_k
from src.ingestion.chunking import ChunkRecord
from src.retrieval.base import RankedChunk
from src.retrieval.dense import build_dense_index, search_dense
from src.retrieval.embeddings import embed_texts
from src.retrieval.sparse import build_bm25_index, search_bm25

CORPUS = [
    ChunkRecord(chunk_id="c1", source_file="finance.pdf", page_number=1, text=(
        "Quarterly revenue grew twelve percent thanks to strong subscription sales growth."
    ), token_count=10),
    ChunkRecord(chunk_id="c2", source_file="finance.pdf", page_number=2, text=(
        "Net profit margin improved after operating costs were cut across every region."
    ), token_count=11),
    ChunkRecord(chunk_id="c3", source_file="travel.pdf", page_number=1, text=(
        "The capital city is known for its museums, parks, and a centuries-old castle."
    ), token_count=13),
    ChunkRecord(chunk_id="c4", source_file="hr.pdf", page_number=1, text=(
        "Staff enjoyed an outdoor picnic near the river during the last quarter."
    ), token_count=12),
]


def _build_stores():
    embeddings = embed_texts([c.text for c in CORPUS])
    dense_store = build_dense_index(embeddings, CORPUS)
    bm25_store = build_bm25_index(CORPUS)
    return dense_store, bm25_store


def test_search_dense_ranks_semantically_relevant_chunk_first():
    dense_store, _ = _build_stores()
    # No shared keywords with c1's text, but semantically about the same topic.
    results = search_dense("How did quarterly earnings and sales perform?", dense_store, top_k=2)

    assert results
    assert results[0].chunk_id == "c1"


def test_search_bm25_ranks_exact_keyword_match_first():
    _, bm25_store = _build_stores()
    results = search_bm25("centuries-old castle museums capital city", bm25_store, top_k=2)

    assert results
    assert results[0].chunk_id == "c3"


def test_reciprocal_rank_fusion_recovers_document_missed_by_one_retriever():
    # Dense ranks the keyword-heavy doc low; sparse ranks the semantic-paraphrase doc low.
    # Neither retriever alone gets both relevant docs into top-2; RRF should.
    dense_ranked = [
        RankedChunk(chunk_id="cA", source_file="f.pdf", page_number=1, text="", score=0.9, rank=1),
        RankedChunk(chunk_id="cX", source_file="f.pdf", page_number=2, text="", score=0.5, rank=2),
        RankedChunk(chunk_id="cB", source_file="f.pdf", page_number=3, text="", score=0.4, rank=3),
    ]
    sparse_ranked = [
        RankedChunk(chunk_id="cB", source_file="f.pdf", page_number=3, text="", score=5.0, rank=1),
        RankedChunk(chunk_id="cY", source_file="f.pdf", page_number=4, text="", score=3.0, rank=2),
        RankedChunk(chunk_id="cA", source_file="f.pdf", page_number=1, text="", score=1.0, rank=3),
    ]
    relevant = {"cA", "cB"}

    fused = reciprocal_rank_fusion(dense_ranked, sparse_ranked)
    fused_ids = [f.chunk_id for f in fused]

    dense_only_ids = [r.chunk_id for r in dense_ranked]
    sparse_only_ids = [r.chunk_id for r in sparse_ranked]

    hybrid_recall = recall_at_k(fused_ids, relevant, k=2)
    dense_recall = recall_at_k(dense_only_ids, relevant, k=2)
    sparse_recall = recall_at_k(sparse_only_ids, relevant, k=2)

    assert hybrid_recall >= max(dense_recall, sparse_recall)
    assert hybrid_recall == 1.0  # cA and cB both make it into the fused top-2


def test_retrieve_hybrid_mode_returns_fused_scores_with_both_ranks():
    dense_store, bm25_store = _build_stores()
    results = retrieve("quarterly revenue and profit performance", "hybrid", dense_store, bm25_store, top_k=3)

    assert results
    assert all(r.fused_score > 0 for r in results)
    assert any(r.dense_rank is not None for r in results)


def test_retrieve_dense_mode_matches_search_dense():
    dense_store, bm25_store = _build_stores()
    results = retrieve("quarterly revenue and profit performance", "dense", dense_store, bm25_store, top_k=2)

    assert all(r.sparse_rank is None for r in results)
    assert all(r.dense_rank is not None for r in results)
