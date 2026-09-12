from chunking import ChunkRecord
from embeddings import embed_texts
from evaluator import precision_at_k, recall_at_k
from retriever import retrieve
from vector_store import build_index


def make_store(texts: list[str]):
    chunks = [
        ChunkRecord(chunk_id=f"chunk_{i:05d}", source_file="doc.pdf", page_number=1, text=text, token_count=len(text.split()))
        for i, text in enumerate(texts)
    ]
    embeddings = embed_texts(texts)
    return build_index(embeddings, chunks)


def test_retrieve_returns_top_k_ranked_by_score():
    store = make_store(
        [
            "The quick brown fox jumps over the lazy dog.",
            "Quarterly revenue grew by twelve percent year over year.",
            "A fox is a small carnivorous mammal related to dogs.",
        ]
    )

    results, elapsed = retrieve("Tell me about foxes", store, top_k=2)

    assert elapsed >= 0.0
    assert len(results) == 2
    assert results[0].score >= results[1].score
    retrieved_texts = {r.text for r in results}
    assert "Quarterly revenue grew by twelve percent year over year." not in retrieved_texts


def test_retrieve_respects_top_k_larger_than_store_size():
    store = make_store(["Only one chunk here."])

    results, _ = retrieve("anything", store, top_k=5)

    assert len(results) == 1
    assert results[0].source_file == "doc.pdf"


def test_retrieve_applies_score_threshold():
    store = make_store(
        [
            "Paris is the capital of France.",
            "Bananas are a good source of potassium.",
        ]
    )

    results, _ = retrieve("What is the capital of France?", store, top_k=2, score_threshold=0.9)

    assert all(r.score >= 0.9 for r in results)


def test_retrieve_empty_query_returns_no_results():
    store = make_store(["Some content."])

    results, elapsed = retrieve("   ", store, top_k=3)

    assert results == []
    assert elapsed >= 0.0


def test_retrieve_empty_store_returns_no_results():
    results, elapsed = retrieve("a question", None, top_k=3)

    assert results == []
    assert elapsed >= 0.0


def test_recall_at_k_computes_hits_and_misses():
    result = recall_at_k(
        retrieved_chunk_ids=["chunk_00000", "chunk_00001"],
        relevant_chunk_ids=["chunk_00001", "chunk_00002"],
    )

    assert result.recall_at_k == 0.5
    assert result.retrieved_relevant == ["chunk_00001"]
    assert result.missed_relevant == ["chunk_00002"]


def test_recall_at_k_with_no_relevant_chunks_returns_zero():
    result = recall_at_k(retrieved_chunk_ids=["chunk_00000"], relevant_chunk_ids=[])

    assert result.recall_at_k == 0.0
    assert result.retrieved_relevant == []
    assert result.missed_relevant == []


def test_precision_at_k_computes_fraction_relevant():
    precision = precision_at_k(
        retrieved_chunk_ids=["chunk_00000", "chunk_00001", "chunk_00002"],
        relevant_chunk_ids=["chunk_00001"],
    )

    assert precision == 1 / 3


def test_precision_at_k_empty_retrieval_returns_zero():
    assert precision_at_k(retrieved_chunk_ids=[], relevant_chunk_ids=["chunk_00000"]) == 0.0
