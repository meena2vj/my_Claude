"""BM25 sparse keyword index build + search (rank-bm25)."""

from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from src.ingestion.chunking import ChunkRecord
from src.retrieval.base import RankedChunk
from src.utils.helpers import tokenize_words


class BM25IndexError(Exception):
    """Raised when the BM25 index cannot be built from the given inputs."""


@dataclass
class BM25Store:
    bm25: BM25Okapi
    chunks: list[ChunkRecord]


def build_bm25_index(chunks: list[ChunkRecord]) -> BM25Store:
    """Build a BM25Okapi index over tokenized chunk text."""
    if not chunks:
        raise BM25IndexError("Cannot build a BM25 index from zero chunks.")

    tokenized_corpus = [tokenize_words(chunk.text) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    return BM25Store(bm25=bm25, chunks=chunks)


def search_bm25(query: str, store: BM25Store | None, top_k: int) -> list[RankedChunk]:
    """Tokenize the query and return the top-k BM25-scored chunks, ranked descending."""
    if not query or not query.strip():
        return []
    if store is None or len(store.chunks) == 0:
        return []

    query_tokens = tokenize_words(query)
    if not query_tokens:
        return []

    scores = store.bm25.get_scores(query_tokens)
    k = min(top_k, len(store.chunks))
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]

    results: list[RankedChunk] = []
    for rank, idx in enumerate(ranked_indices, start=1):
        if scores[idx] <= 0:
            continue  # BM25 score of 0 means no term overlap at all — not a real match
        chunk = store.chunks[idx]
        results.append(
            RankedChunk(
                chunk_id=chunk.chunk_id,
                source_file=chunk.source_file,
                page_number=chunk.page_number,
                text=chunk.text,
                score=float(scores[idx]),
                rank=rank,
                is_suspicious=chunk.is_suspicious,
            )
        )
    return results
