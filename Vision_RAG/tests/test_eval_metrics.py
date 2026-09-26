import math

import pytest

from utils.evaluation import (
    diversity,
    format_comparison_table,
    groundedness_score,
    hit_rate,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from utils.data_models import ModeMetrics

RETRIEVED = ["c3", "c1", "c5", "c2", "c4"]
RELEVANT = {"c1", "c2"}


def test_precision_at_k_counts_relevant_within_top_k():
    assert precision_at_k(RETRIEVED, RELEVANT, k=2) == 0.5  # c3, c1 -> 1 hit / 2
    assert precision_at_k(RETRIEVED, RELEVANT, k=4) == 0.5  # c3,c1,c5,c2 -> 2 hits / 4


def test_precision_at_k_zero_k_returns_zero():
    assert precision_at_k(RETRIEVED, RELEVANT, k=0) == 0.0


def test_precision_at_k_empty_retrieval_returns_zero():
    assert precision_at_k([], RELEVANT, k=5) == 0.0


def test_recall_at_k_counts_relevant_found():
    assert recall_at_k(RETRIEVED, RELEVANT, k=2) == 0.5  # found c1 only / 2 relevant
    assert recall_at_k(RETRIEVED, RELEVANT, k=4) == 1.0  # found c1 and c2 / 2 relevant


def test_recall_at_k_no_relevant_returns_zero():
    assert recall_at_k(RETRIEVED, set(), k=5) == 0.0


def test_hit_rate_true_when_any_relevant_in_top_k():
    assert hit_rate(RETRIEVED, RELEVANT, k=2) == 1.0  # c1 is in top 2
    assert hit_rate(["c9", "c8"], RELEVANT, k=2) == 0.0


def test_mrr_uses_first_relevant_rank():
    # first relevant hit ("c1") is at rank 2
    assert mrr(RETRIEVED, RELEVANT) == 0.5


def test_mrr_zero_when_no_relevant_found():
    assert mrr(["c9", "c8"], RELEVANT) == 0.0


def test_ndcg_at_k_perfect_ranking_is_one():
    perfect = ["c1", "c2", "c9", "c8"]
    assert math.isclose(ndcg_at_k(perfect, RELEVANT, k=4), 1.0)


def test_ndcg_at_k_worse_ranking_is_lower_than_perfect():
    perfect = ["c1", "c2", "c9", "c8"]
    worse = ["c9", "c8", "c1", "c2"]
    assert ndcg_at_k(worse, RELEVANT, k=4) < ndcg_at_k(perfect, RELEVANT, k=4)


def test_ndcg_at_k_no_relevant_returns_zero():
    assert ndcg_at_k(RETRIEVED, set(), k=4) == 0.0


def test_diversity_all_distinct_sources_is_one():
    assert diversity(["a.png", "b.png", "c.png"], k=3) == 1.0


def test_diversity_single_source_dominates_top_k():
    assert diversity(["a.png", "a.png", "a.png"], k=3) == pytest.approx(1 / 3)


def test_diversity_empty_returns_zero():
    assert diversity([], k=5) == 0.0


def test_groundedness_score_full_overlap_is_one():
    context = "the invoice total is five hundred dollars due march third"
    answer = "the invoice total is five hundred dollars"
    assert groundedness_score(answer, context) == 1.0


def test_groundedness_score_no_overlap_is_zero():
    context = "the invoice total is five hundred dollars due march third"
    answer = "completely unrelated refund policy statement here"
    assert groundedness_score(answer, context) == 0.0


def test_groundedness_score_empty_answer_words_is_one():
    assert groundedness_score("42", "some context") == 1.0


def test_format_comparison_table_includes_all_modes():
    results = [
        ModeMetrics(mode="dense", precision_at_k=0.5, recall_at_k=0.6, mrr=0.7, ndcg_at_k=0.8, hit_rate=1.0, diversity=0.9),
        ModeMetrics(mode="sparse", precision_at_k=0.4, recall_at_k=0.5, mrr=0.6, ndcg_at_k=0.7, hit_rate=1.0, diversity=0.8),
        ModeMetrics(mode="hybrid", precision_at_k=0.6, recall_at_k=0.7, mrr=0.8, ndcg_at_k=0.9, hit_rate=1.0, diversity=1.0),
    ]
    table = format_comparison_table(results)
    assert "dense" in table and "sparse" in table and "hybrid" in table
