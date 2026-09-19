"""FAISS-backed retrieval over uploaded business-context documents.

Rebuilt on demand from `business_context_chunks` (never persisted to disk) --
cheap at this scale and avoids stale-index bugs when documents change
mid-session. Retrieved text is qualitative-only: callers must never treat a
number found here as authoritative -- see `tools/analysis_ops.py`'s
narrative-validation guardrail for the enforcement side of that rule.
"""

import uuid
from datetime import datetime, timezone

import faiss
import numpy as np

from config.settings import RAG_TOP_K
from graph.state import BusinessContextDoc, ContextChunk
from services.chunking import chunk_text
from services.embeddings import embed_texts
from tools.pdf_text_extract import extract_pages


def ingest_document(
    filename: str, raw_bytes: bytes, extension: str
) -> tuple[BusinessContextDoc, list[ContextChunk]]:
    doc_id = str(uuid.uuid4())
    doc = BusinessContextDoc(
        doc_id=doc_id, filename=filename, upload_ts=datetime.now(timezone.utc).isoformat()
    )

    if extension == ".pdf":
        pages = extract_pages(raw_bytes)
    else:
        pages = [(1, raw_bytes.decode("utf-8", errors="ignore"))]

    chunks: list[ContextChunk] = []
    for page_num, page_text in pages:
        for piece in chunk_text(page_text):
            piece = piece.strip()
            if not piece:
                continue
            chunks.append(
                ContextChunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc_id,
                    filename=filename,
                    page=page_num,
                    text=piece,
                    token_count=len(piece.split()),
                )
            )
    return doc, chunks


def retrieve(chunks: list[ContextChunk], query: str, top_k: int = RAG_TOP_K) -> list[ContextChunk]:
    if not chunks or not query.strip():
        return []

    doc_vectors = np.asarray(embed_texts([c.text for c in chunks]), dtype="float32")
    query_vector = np.asarray(embed_texts([query]), dtype="float32")

    index = faiss.IndexFlatIP(doc_vectors.shape[1])
    index.add(doc_vectors)

    k = min(top_k, len(chunks))
    _, indices = index.search(query_vector, k)
    return [chunks[i] for i in indices[0] if i != -1]
