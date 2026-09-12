import pytest

from src.evaluation.metrics import (
    EvalCase,
    groundedness_score,
    hit_rate,
    mrr,
    ndcg_at_k,
    recall_at_k,
    run_evaluation,
)
from src.ingestion.chunking import ChunkRecord
from src.retrieval.dense import build_dense_index
from src.retrieval.embeddings import embed_texts
from src.retrieval.sparse import build_bm25_index

RETRIEVED = ["a", "b", "c", "d"]
RELEVANT = {"b", "d"}


def test_recall_at_k_partial_and_full():
    assert recall_at_k(RETRIEVED, RELEVANT, k=2) == pytest.approx(0.5)
    assert recall_at_k(RETRIEVED, RELEVANT, k=4) == pytest.approx(1.0)


def test_recall_at_k_no_relevant_docs_returns_zero():
    assert recall_at_k(RETRIEVED, set(), k=4) == 0.0


def test_hit_rate_true_and_false():
    assert hit_rate(RETRIEVED, RELEVANT, k=2) == 1.0
    assert hit_rate(["x", "y"], {"b"}, k=2) == 0.0


def test_mrr_reciprocal_of_first_relevant_rank():
    assert mrr(RETRIEVED, RELEVANT) == pytest.approx(0.5)  # first hit "b" at rank 2


def test_mrr_zero_when_no_relevant_present():
    assert mrr(["x", "y"], {"z"}) == 0.0


def test_ndcg_at_k_matches_hand_computed_value():
    assert ndcg_at_k(RETRIEVED, RELEVANT, k=4) == pytest.approx(0.6509, abs=1e-3)


def test_ndcg_at_k_perfect_ranking_is_one():
    assert ndcg_at_k(["b", "d", "a", "c"], RELEVANT, k=4) == pytest.approx(1.0)


def test_groundedness_score_full_and_zero():
    grounded = groundedness_score(
        "Revenue grew twelve percent", "Quarterly revenue grew twelve percent driven by sales"
    )
    ungrounded = groundedness_score(
        "Totally unrelated spaceship launch details", "Quarterly revenue grew twelve percent driven by sales"
    )
    assert grounded == pytest.approx(1.0)
    assert ungrounded == pytest.approx(0.0)


def test_run_evaluation_hybrid_recall_at_least_matches_best_single_mode():
    corpus = [
        ChunkRecord(chunk_id="c1", source_file="finance.pdf", page_number=1, text=(
            "Quarterly revenue grew twelve percent thanks to strong subscription sales growth."
        )),
        ChunkRecord(chunk_id="c2", source_file="finance.pdf", page_number=2, text=(
            "Net profit margin improved after operating costs were cut across every region."
        )),
        ChunkRecord(chunk_id="c3", source_file="travel.pdf", page_number=1, text=(
            "The capital city is known for its museums, parks, and a centuries-old castle."
        )),
        ChunkRecord(chunk_id="c4", source_file="hr.pdf", page_number=1, text=(
            "Staff enjoyed an outdoor picnic near the river during the last quarter."
        )),
    ]
    dense_store = build_dense_index(embed_texts([c.text for c in corpus]), corpus)
    bm25_store = build_bm25_index(corpus)

    cases = [
        EvalCase(query="How did quarterly earnings and sales perform?", relevant_chunk_ids={"c1"}),
        EvalCase(query="centuries-old castle museums capital city", relevant_chunk_ids={"c3"}),
    ]

    results_by_mode = {m.mode: m for m in run_evaluation(cases, dense_store, bm25_store, top_k=2)}

    hybrid_recall = results_by_mode["hybrid"].recall_at_k
    dense_recall = results_by_mode["dense"].recall_at_k
    sparse_recall = results_by_mode["sparse"].recall_at_k

    assert hybrid_recall >= max(dense_recall, sparse_recall) - 1e-9
