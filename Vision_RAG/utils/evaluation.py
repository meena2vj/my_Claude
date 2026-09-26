"""Retrieval and generation evaluation metrics.

Pure functions operate on plain chunk-id/source lists so they're trivially
unit testable; `run_evaluation` wires them to the real dense/sparse/hybrid
retrievers to produce the dense-vs-sparse-vs-hybrid comparison table.

Extends Hybrid_RAG's metric set with `precision_at_k` and `diversity`, both
required by this project's CLAUDE.md Evaluation Framework (Retrieval Metrics:
Precision@k, Recall@k, MRR, NDCG@k, Hit Rate, "Diversity of retrieved sources").
"""

import math

from config import RETRIEVAL_MODES
from utils.data_models import EvaluationCase, ModeMetrics
from utils.fusion import retrieve
from utils.helpers import tokenize_words


def precision_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = len(set(top_k) & relevant_ids)
    return hits / len(top_k)


def recall_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    hits = len(set(retrieved_ids[:k]) & relevant_ids)
    return hits / len(relevant_ids)


def hit_rate(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    if not relevant_ids:
        return 0.0
    return 1.0 if set(retrieved_ids[:k]) & relevant_ids else 0.0


def mrr(retrieved_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Binary-relevance NDCG@k."""
    if not relevant_ids:
        return 0.0

    dcg = 0.0
    for rank, chunk_id in enumerate(retrieved_ids[:k], start=1):
        relevance = 1.0 if chunk_id in relevant_ids else 0.0
        dcg += relevance / math.log2(rank + 1)

    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def diversity(retrieved_sources: list[str], k: int) -> float:
    """Fraction of top-k results that come from distinct source documents.

    1.0 means every retrieved chunk in the top-k is from a different source
    file; lower values mean the top-k is dominated by one or few documents.
    """
    top_k = retrieved_sources[:k]
    if not top_k:
        return 0.0
    return len(set(top_k)) / len(top_k)


def groundedness_score(answer: str, context_text: str) -> float:
    """Fraction of the answer's content words (len > 3) found in the retrieved context."""
    answer_words = [w for w in tokenize_words(answer) if len(w) > 3]
    if not answer_words:
        return 1.0
    context_words = set(tokenize_words(context_text))
    if not context_words:
        return 0.0
    return sum(1 for w in answer_words if w in context_words) / len(answer_words)


def evaluate_mode(
    cases: list[EvaluationCase],
    mode: str,
    dense_store,
    bm25_store,
    top_k: int,
) -> ModeMetrics:
    """Average retrieval metrics for one retrieval mode across all eval cases."""
    precisions, recalls, mrrs, ndcgs, hits, diversities = [], [], [], [], [], []
    for case in cases:
        fused = retrieve(case.query, mode, dense_store, bm25_store, top_k)
        retrieved_ids = [c.chunk_id for c in fused]
        retrieved_sources = [c.source_file for c in fused]
        precisions.append(precision_at_k(retrieved_ids, case.relevant_chunk_ids, top_k))
        recalls.append(recall_at_k(retrieved_ids, case.relevant_chunk_ids, top_k))
        mrrs.append(mrr(retrieved_ids, case.relevant_chunk_ids))
        ndcgs.append(ndcg_at_k(retrieved_ids, case.relevant_chunk_ids, top_k))
        hits.append(hit_rate(retrieved_ids, case.relevant_chunk_ids, top_k))
        diversities.append(diversity(retrieved_sources, top_k))

    n = len(cases) or 1
    return ModeMetrics(
        mode=mode,
        precision_at_k=sum(precisions) / n,
        recall_at_k=sum(recalls) / n,
        mrr=sum(mrrs) / n,
        ndcg_at_k=sum(ndcgs) / n,
        hit_rate=sum(hits) / n,
        diversity=sum(diversities) / n,
    )


def run_evaluation(
    cases: list[EvaluationCase],
    dense_store,
    bm25_store,
    top_k: int,
) -> list[ModeMetrics]:
    """Evaluate dense, sparse, and hybrid retrieval on the same eval cases."""
    return [evaluate_mode(cases, mode, dense_store, bm25_store, top_k) for mode in RETRIEVAL_MODES]


def format_comparison_table(results: list[ModeMetrics]) -> str:
    header = f"{'Mode':<10}{'P@k':>8}{'Recall@k':>10}{'MRR':>8}{'NDCG@k':>8}{'HitRate':>9}{'Diversity':>11}"
    lines = [header, "-" * len(header)]
    for r in results:
        lines.append(
            f"{r.mode:<10}{r.precision_at_k:>8.3f}{r.recall_at_k:>10.3f}{r.mrr:>8.3f}"
            f"{r.ndcg_at_k:>8.3f}{r.hit_rate:>9.3f}{r.diversity:>11.3f}"
        )
    return "\n".join(lines)
