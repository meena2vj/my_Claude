"""Domain models shared across ingestion, retrieval, generation, and evaluation.

Names follow CLAUDE.md's "Implementation Guidance > Data Model" section exactly:
DocumentRecord, PageRecord, ChunkRecord, RetrievalResult, AnswerRecord, EvaluationCase.
`RankedChunk` is internal plumbing (the shared shape dense/sparse retrieval emit
before fusion) — not named in the spec, but needed for fusion to be symmetric.
"""

from dataclasses import dataclass, field


@dataclass
class DocumentRecord:
    document_id: str
    file_name: str
    source_type: str  # "image" or "pdf"
    page_count: int


@dataclass
class PageRecord:
    document_id: str
    file_name: str
    page_number: int  # 1-indexed
    page_text: str
    is_empty: bool
    ocr_confidence: float  # 0.0-1.0, mean word confidence from OCR
    source_type: str  # "image" or "pdf_page"


@dataclass
class ChunkRecord:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    token_count: int = 0
    ocr_confidence: float = 1.0
    is_suspicious: bool = False  # set by guardrails.scan_chunks; never trust silently


@dataclass
class RankedChunk:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    score: float  # native to the retriever (cosine sim for dense, BM25 score for sparse)
    rank: int  # 1-indexed rank within this retriever's result list
    is_suspicious: bool = False


@dataclass
class RetrievalResult:
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


@dataclass
class AnswerRecord:
    answer: str
    latency_seconds: float
    answer_token_count: int
    error: str | None = None
    flagged: bool = False


@dataclass
class EvaluationCase:
    query: str
    relevant_chunk_ids: set[str]


@dataclass
class ModeMetrics:
    mode: str
    precision_at_k: float
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    hit_rate: float
    diversity: float
