"""Shared result shape for dense and sparse retrieval, so fusion is symmetric."""

from dataclasses import dataclass


@dataclass
class RankedChunk:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    score: float  # native to the retriever (cosine sim for dense, BM25 score for sparse)
    rank: int  # 1-indexed rank within this retriever's result list
    is_suspicious: bool = False
