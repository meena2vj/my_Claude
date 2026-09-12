"""FAISS dense vector index build + similarity search."""

from dataclasses import dataclass

import faiss
import numpy as np

from src.ingestion.chunking import ChunkRecord
from src.retrieval.base import RankedChunk
from src.retrieval.embeddings import embed_texts


class VectorStoreError(Exception):
    """Raised when the FAISS index cannot be built from the given inputs."""


@dataclass
class VectorStore:
    index: faiss.Index
    chunks: list[ChunkRecord]
    dimension: int


def build_dense_index(embeddings: np.ndarray, chunks: list[ChunkRecord]) -> VectorStore:
    """Build a FAISS inner-product index over normalized embeddings (= cosine similarity)."""
    if embeddings.shape[0] != len(chunks):
        raise VectorStoreError(
            f"Embedding count ({embeddings.shape[0]}) does not match chunk count ({len(chunks)})."
        )
    if embeddings.shape[0] == 0:
        raise VectorStoreError("Cannot build a FAISS index from zero chunks.")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)
    return VectorStore(index=index, chunks=chunks, dimension=dimension)


def search_dense(query: str, store: VectorStore | None, top_k: int) -> list[RankedChunk]:
    """Embed the query and run FAISS top-k cosine similarity search."""
    if not query or not query.strip():
        return []
    if store is None or len(store.chunks) == 0:
        return []

    query_embedding = embed_texts([query])
    k = min(top_k, len(store.chunks))
    scores, indices = store.index.search(query_embedding, k)

    results: list[RankedChunk] = []
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), start=1):
        if idx < 0:
            continue
        chunk = store.chunks[idx]
        results.append(
            RankedChunk(
                chunk_id=chunk.chunk_id,
                source_file=chunk.source_file,
                page_number=chunk.page_number,
                text=chunk.text,
                score=float(score),
                rank=rank,
                is_suspicious=chunk.is_suspicious,
            )
        )
    return results
