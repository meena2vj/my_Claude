"""FAISS vector index build/rebuild, with metadata mapped back to chunks."""

from dataclasses import dataclass

import faiss
import numpy as np

from chunking import ChunkRecord


class VectorStoreError(Exception):
    """Raised when the FAISS index cannot be built from the given inputs."""


@dataclass
class VectorStore:
    index: faiss.Index
    chunks: list[ChunkRecord]
    dimension: int


def build_index(embeddings: np.ndarray, chunks: list[ChunkRecord]) -> VectorStore:
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


def rebuild_index(embeddings: np.ndarray, chunks: list[ChunkRecord]) -> VectorStore:
    """Rebuild the index from scratch (e.g. after reprocessing documents)."""
    return build_index(embeddings, chunks)
