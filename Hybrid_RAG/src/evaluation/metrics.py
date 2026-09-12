"""Retrieval and generation evaluation metrics.

Pure functions operate on plain chunk-id lists so they're trivially unit
testable; `run_evaluation` wires them to the real dense/sparse/hybrid
retrievers to produce the dense-vs-sparse-vs-hybrid comparison table.
"""

import math
from dataclasses import dataclass

from config import RETRIEVAL_MODES
from src.hybrid.fusion import retrieve
from src.hybrid.guardrails import check_grounding
from src.retrieval.base import RankedChunk
from src.retrieval.dense import VectorStore
from src.retrieval.sparse import BM25Store
from src.utils.helpers import tokenize_words


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


def groundedness_score(answer: str, context_text: str) -> float:
    """Fraction of the answer's content words (len > 3) found in the retrieved context."""
    answer_words = [w for w in tokenize_words(answer) if len(w) > 3]
    if not answer_words:
        return 1.0
    context_words = set(tokenize_words(context_text))
    if not context_words:
        return 0.0
    return sum(1 for w in answer_words if w in context_words) / len(answer_words)


@dataclass
class EvalCase:
    query: str
    relevant_chunk_ids: set[str]


@dataclass
class ModeMetrics:
    mode: str
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    hit_rate: float


def evaluate_mode(
    cases: list[EvalCase],
    mode: str,
    dense_store: VectorStore | None,
    bm25_store: BM25Store | None,
    top_k: int,
) -> ModeMetrics:
    """Average retrieval metrics for one retrieval mode across all eval cases."""
    recalls, mrrs, ndcgs, hits = [], [], [], []
    for case in cases:
        fused = retrieve(case.query, mode, dense_store, bm25_store, top_k)
        retrieved_ids = [c.chunk_id for c in fused]
        recalls.append(recall_at_k(retrieved_ids, case.relevant_chunk_ids, top_k))
        mrrs.append(mrr(retrieved_ids, case.relevant_chunk_ids))
        ndcgs.append(ndcg_at_k(retrieved_ids, case.relevant_chunk_ids, top_k))
        hits.append(hit_rate(retrieved_ids, case.relevant_chunk_ids, top_k))

    n = len(cases) or 1
    return ModeMetrics(
        mode=mode,
        recall_at_k=sum(recalls) / n,
        mrr=sum(mrrs) / n,
        ndcg_at_k=sum(ndcgs) / n,
        hit_rate=sum(hits) / n,
    )


def run_evaluation(
    cases: list[EvalCase],
    dense_store: VectorStore | None,
    bm25_store: BM25Store | None,
    top_k: int,
) -> list[ModeMetrics]:
    """Evaluate dense, sparse, and hybrid retrieval on the same eval cases."""
    return [evaluate_mode(cases, mode, dense_store, bm25_store, top_k) for mode in RETRIEVAL_MODES]


def format_comparison_table(results: list[ModeMetrics]) -> str:
    header = f"{'Mode':<10}{'Recall@k':>10}{'MRR':>10}{'NDCG@k':>10}{'HitRate':>10}"
    lines = [header, "-" * len(header)]
    for r in results:
        lines.append(f"{r.mode:<10}{r.recall_at_k:>10.3f}{r.mrr:>10.3f}{r.ndcg_at_k:>10.3f}{r.hit_rate:>10.3f}")
    return "\n".join(lines)
