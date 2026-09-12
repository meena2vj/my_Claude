"""Lightweight RAG evaluation metrics.

Without ground truth, relevance/groundedness metrics are heuristic
(embedding-similarity based) and are always labeled as such — never
presented as exact truth. Recall@K / Precision@K become exact whenever the
caller supplies a reference set of expected relevant chunk ids per question.
"""

from dataclasses import dataclass

import numpy as np

from embeddings import embed_texts
from retriever import RetrievalResult


@dataclass
class EvaluationResult:
    context_relevance: float | None  # heuristic: mean retrieval similarity score
    answer_relevance: float | None  # heuristic: embedding similarity(question, answer)
    groundedness: float | None  # heuristic: embedding similarity(answer, retrieved context)
    source_coverage: float  # distinct (file, page) sources / chunks retrieved
    retrieval_latency_seconds: float
    response_latency_seconds: float
    is_heuristic: bool = True


@dataclass
class RecallResult:
    recall_at_k: float
    retrieved_relevant: list[str]
    missed_relevant: list[str]


def _cosine_similarity(vector_a: np.ndarray, vector_b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(vector_a) * np.linalg.norm(vector_b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(vector_a, vector_b) / denominator)


def context_relevance_score(results: list[RetrievalResult]) -> float | None:
    """Heuristic: average FAISS similarity score of the retrieved chunks."""
    if not results:
        return None
    return sum(result.score for result in results) / len(results)


def answer_relevance_score(question: str, answer: str) -> float | None:
    """Heuristic: embedding cosine similarity between the question and the answer."""
    if not question.strip() or not answer.strip():
        return None
    vectors = embed_texts([question, answer])
    return _cosine_similarity(vectors[0], vectors[1])


def groundedness_score(answer: str, results: list[RetrievalResult]) -> float | None:
    """Heuristic faithfulness proxy: embedding similarity between the answer and its retrieved context."""
    if not answer.strip() or not results:
        return None
    context_text = " ".join(result.text for result in results)
    vectors = embed_texts([answer, context_text])
    return _cosine_similarity(vectors[0], vectors[1])


def source_coverage_score(results: list[RetrievalResult]) -> float:
    """Fraction of retrieved chunks that come from distinct (file, page) sources."""
    if not results:
        return 0.0
    distinct_sources = {(result.source_file, result.page_number) for result in results}
    return len(distinct_sources) / len(results)


def evaluate(
    question: str,
    answer: str,
    results: list[RetrievalResult],
    retrieval_latency_seconds: float,
    response_latency_seconds: float,
) -> EvaluationResult:
    return EvaluationResult(
        context_relevance=context_relevance_score(results),
        answer_relevance=answer_relevance_score(question, answer),
        groundedness=groundedness_score(answer, results),
        source_coverage=source_coverage_score(results),
        retrieval_latency_seconds=retrieval_latency_seconds,
        response_latency_seconds=response_latency_seconds,
    )


def recall_at_k(retrieved_chunk_ids: list[str], relevant_chunk_ids: list[str]) -> RecallResult:
    """Recall = Relevant Retrieved / Total Relevant, for test datasets with known relevant chunks."""
    if not relevant_chunk_ids:
        return RecallResult(recall_at_k=0.0, retrieved_relevant=[], missed_relevant=[])

    retrieved_set = set(retrieved_chunk_ids)
    relevant_set = set(relevant_chunk_ids)
    hit = retrieved_set & relevant_set
    missed = relevant_set - retrieved_set

    return RecallResult(
        recall_at_k=len(hit) / len(relevant_set),
        retrieved_relevant=sorted(hit),
        missed_relevant=sorted(missed),
    )


def precision_at_k(retrieved_chunk_ids: list[str], relevant_chunk_ids: list[str]) -> float:
    """Precision@K = Relevant Retrieved / K, for test datasets with known relevant chunks."""
    if not retrieved_chunk_ids:
        return 0.0
    relevant_set = set(relevant_chunk_ids)
    hit = sum(1 for chunk_id in retrieved_chunk_ids if chunk_id in relevant_set)
    return hit / len(retrieved_chunk_ids)
