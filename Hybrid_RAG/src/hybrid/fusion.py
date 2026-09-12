"""Reciprocal Rank Fusion (RRF) combining dense + sparse rank lists, and the
retrieval-mode orchestrator (dense / sparse / hybrid) used by the UI, eval, and tests."""

from dataclasses import dataclass

from config import CANDIDATE_POOL_MULTIPLIER, RRF_K_DEFAULT
from src.retrieval.base import RankedChunk
from src.retrieval.dense import VectorStore, search_dense
from src.retrieval.sparse import BM25Store, search_bm25


@dataclass
class FusedChunk:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    fused_score: float
    dense_rank: int | None
    sparse_rank: int | None
    dense_score: float | None
    sparse_score: float | None
    is_suspicious: bool = False


def reciprocal_rank_fusion(
    dense_ranked: list[RankedChunk],
    sparse_ranked: list[RankedChunk],
    k: int = RRF_K_DEFAULT,
) -> list[FusedChunk]:
    """Fuse two ranked lists with RRF: score(d) = sum(1 / (k + rank_i(d))).

    A chunk appearing in only one list still gets a (smaller) fused score from
    that list alone — this is what lets hybrid retrieval recall documents that
    only one of the two retrievers surfaced.
    """
    by_id: dict[str, FusedChunk] = {}

    for item in dense_ranked:
        by_id[item.chunk_id] = FusedChunk(
            chunk_id=item.chunk_id,
            source_file=item.source_file,
            page_number=item.page_number,
            text=item.text,
            fused_score=1.0 / (k + item.rank),
            dense_rank=item.rank,
            sparse_rank=None,
            dense_score=item.score,
            sparse_score=None,
            is_suspicious=item.is_suspicious,
        )

    for item in sparse_ranked:
        existing = by_id.get(item.chunk_id)
        contribution = 1.0 / (k + item.rank)
        if existing is None:
            by_id[item.chunk_id] = FusedChunk(
                chunk_id=item.chunk_id,
                source_file=item.source_file,
                page_number=item.page_number,
                text=item.text,
                fused_score=contribution,
                dense_rank=None,
                sparse_rank=item.rank,
                dense_score=None,
                sparse_score=item.score,
                is_suspicious=item.is_suspicious,
            )
        else:
            existing.fused_score += contribution
            existing.sparse_rank = item.rank
            existing.sparse_score = item.score
            existing.is_suspicious = existing.is_suspicious or item.is_suspicious

    return sorted(by_id.values(), key=lambda c: c.fused_score, reverse=True)


def retrieve(
    query: str,
    mode: str,
    dense_store: VectorStore | None,
    bm25_store: BM25Store | None,
    top_k: int,
    rrf_k: int = RRF_K_DEFAULT,
    candidate_pool_multiplier: int = CANDIDATE_POOL_MULTIPLIER,
) -> list[FusedChunk]:
    """Retrieve top-k chunks in the requested mode: 'dense', 'sparse', or 'hybrid'.

    In 'hybrid' mode each retriever first fetches a larger candidate pool
    (top_k * candidate_pool_multiplier) so RRF has enough overlap signal to
    work with before the final list is truncated to top_k.
    """
    if mode not in ("dense", "sparse", "hybrid"):
        raise ValueError(f"Unknown retrieval mode: {mode!r}")

    if mode == "dense":
        dense_results = search_dense(query, dense_store, top_k)
        return [
            FusedChunk(
                chunk_id=r.chunk_id,
                source_file=r.source_file,
                page_number=r.page_number,
                text=r.text,
                fused_score=r.score,
                dense_rank=r.rank,
                sparse_rank=None,
                dense_score=r.score,
                sparse_score=None,
                is_suspicious=r.is_suspicious,
            )
            for r in dense_results
        ]

    if mode == "sparse":
        sparse_results = search_bm25(query, bm25_store, top_k)
        return [
            FusedChunk(
                chunk_id=r.chunk_id,
                source_file=r.source_file,
                page_number=r.page_number,
                text=r.text,
                fused_score=r.score,
                dense_rank=None,
                sparse_rank=r.rank,
                dense_score=None,
                sparse_score=r.score,
                is_suspicious=r.is_suspicious,
            )
            for r in sparse_results
        ]

    pool_size = top_k * candidate_pool_multiplier
    dense_candidates = search_dense(query, dense_store, pool_size)
    sparse_candidates = search_bm25(query, bm25_store, pool_size)
    fused = reciprocal_rank_fusion(dense_candidates, sparse_candidates, k=rrf_k)
    return fused[:top_k]
