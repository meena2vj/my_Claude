"""Query embedding + FAISS similarity search, with source metadata and latency."""

from dataclasses import dataclass

from config import TOP_K_DEFAULT
from embeddings import embed_texts
from utils import timed
from vector_store import VectorStore


@dataclass
class RetrievalResult:
    chunk_id: str
    source_file: str
    page_number: int
    text: str
    score: float


def retrieve(
    query: str,
    store: VectorStore | None,
    top_k: int = TOP_K_DEFAULT,
    score_threshold: float | None = None,
) -> tuple[list[RetrievalResult], float]:
    """Embed the query, run FAISS top-k similarity search, and return scored results.

    Prefers recall over aggressive filtering: score_threshold is optional and
    off by default.
    """
    results: list[RetrievalResult] = []

    with timed() as timer:
        has_query = bool(query and query.strip())
        has_chunks = store is not None and len(store.chunks) > 0
        if has_query and has_chunks:
            query_embedding = embed_texts([query])
            k = min(top_k, len(store.chunks))
            scores, indices = store.index.search(query_embedding, k)
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue
                if score_threshold is not None and score < score_threshold:
                    continue
                chunk = store.chunks[idx]
                results.append(
                    RetrievalResult(
                        chunk_id=chunk.chunk_id,
                        source_file=chunk.source_file,
                        page_number=chunk.page_number,
                        text=chunk.text,
                        score=float(score),
                    )
                )

    return results, timer.elapsed_seconds
