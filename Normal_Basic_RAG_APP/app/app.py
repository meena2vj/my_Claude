"""Streamlit UI for the Multi-PDF RAG Q&A system."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    GROQ_API_KEY,
    TOP_K_DEFAULT,
    TOP_K_MAX,
    TOP_K_MIN,
)
from chunking import chunk_pages
from embeddings import embed_texts, get_embedding_dimension, load_embedding_model
from evaluator import evaluate, precision_at_k, recall_at_k
from pdf_processor import process_uploaded_pdfs
from rag_chain import generate_answer
from retriever import retrieve
from utils import count_tokens_approx
from vector_store import VectorStoreError, build_index

st.set_page_config(page_title="Multi-PDF RAG Q&A", page_icon="📄", layout="wide")

st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    .app-header {
        padding: 1.25rem 1.5rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #f5f8ff 0%, #eef2fb 100%);
        border: 1px solid #dbe3f3;
        margin-bottom: 0.75rem;
    }
    .app-header h1 {
        margin: 0;
        color: #1f2a44;
        font-size: 1.9rem;
    }
    .app-header p {
        margin: 0.25rem 0 0 0;
        color: #5b6478;
        font-size: 0.95rem;
    }
    .ticker-wrap {
        width: 100%;
        overflow: hidden;
        background: #eef2fb;
        border: 1px solid #dbe3f3;
        border-radius: 8px;
        padding: 0.4rem 0;
        margin-bottom: 1.25rem;
    }
    .ticker {
        display: inline-block;
        white-space: nowrap;
        padding-left: 100%;
        color: #3a4a78;
        font-weight: 600;
        letter-spacing: 0.04em;
        animation: ticker-scroll 18s linear infinite;
    }
    @keyframes ticker-scroll {
        0%   { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }
    div[data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e3e8f2;
        border-radius: 10px;
        padding: 0.6rem 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="app-header">
        <h1>Multi-PDF RAG Q&amp;A</h1>
        <p>Upload multiple PDFs, retrieve grounded context, and get citation-backed answers.</p>
    </div>
    <div class="ticker-wrap">
        <span class="ticker">PDF Q and A &nbsp;•&nbsp; Upload &nbsp;•&nbsp; Chunk &nbsp;•&nbsp; Embed &nbsp;•&nbsp; Retrieve &nbsp;•&nbsp; Ask &nbsp;•&nbsp; Cite &nbsp;•&nbsp; PDF Q and A &nbsp;•&nbsp; Upload &nbsp;•&nbsp; Chunk &nbsp;•&nbsp; Embed &nbsp;•&nbsp; Retrieve &nbsp;•&nbsp; Ask &nbsp;•&nbsp; Cite</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------
_DEFAULTS = {
    "pages": [],
    "chunks": [],
    "embeddings": None,
    "store": None,
    "processing_errors": [],
    "qa_history": [],
    "doc_signature": None,
}
for _key, _value in _DEFAULTS.items():
    st.session_state.setdefault(_key, _value)

# --------------------------------------------------------------------------
# Sidebar configuration
# --------------------------------------------------------------------------
with st.sidebar:
    st.header("Configuration")
    chunk_size = st.slider("Chunk size (characters)", 200, 2000, CHUNK_SIZE, step=50)
    chunk_overlap = st.slider("Chunk overlap (characters)", 0, 500, CHUNK_OVERLAP, step=10)
    top_k = st.slider("Top-K retrieval", TOP_K_MIN, TOP_K_MAX, TOP_K_DEFAULT)
    use_threshold = st.checkbox("Apply similarity score threshold", value=False)
    score_threshold = (
        st.slider("Score threshold", 0.0, 1.0, 0.3, step=0.05) if use_threshold else None
    )

    st.divider()
    if GROQ_API_KEY:
        st.success("Groq API key detected")
    else:
        st.error("GROQ_API_KEY missing — set it in .env to enable answer generation")

    st.divider()
    st.subheader("Recall evaluation (optional)")
    st.caption(
        "Upload a CSV with columns `question,relevant_chunk_ids` "
        "(semicolon-separated chunk ids) to compute exact Recall@K / Precision@K."
    )
    ground_truth_file = st.file_uploader("Ground-truth CSV", type=["csv"], key="ground_truth")

# --------------------------------------------------------------------------
# Upload + process
# --------------------------------------------------------------------------
st.subheader("Upload PDFs")
uploaded_files = st.file_uploader(
    "Upload one or more PDF files", type=["pdf"], accept_multiple_files=True
)

process_clicked = st.button("Process Documents", type="primary", disabled=not uploaded_files)

if process_clicked and uploaded_files:
    signature = tuple(sorted((f.name, f.size) for f in uploaded_files))
    if signature == st.session_state.doc_signature:
        st.info("These documents match the last processed batch — reusing the existing index.")
    else:
        with st.spinner("Extracting text from PDFs..."):
            pages, errors = process_uploaded_pdfs(uploaded_files)
        st.session_state.processing_errors = errors
        st.session_state.pages = pages
        st.session_state.chunks = []
        st.session_state.embeddings = None
        st.session_state.store = None

        if not pages:
            st.session_state.processing_errors.append(
                "No pages could be extracted from the uploaded PDFs."
            )
        else:
            with st.spinner("Chunking text..."):
                chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

            if not chunks:
                st.session_state.processing_errors.append(
                    "No extractable text was found in the uploaded PDFs "
                    "(they may be scanned images without OCR text)."
                )
            else:
                st.session_state.chunks = chunks
                try:
                    with st.spinner("Generating embeddings..."):
                        model = load_embedding_model()
                        embeddings = embed_texts([c.text for c in chunks], model=model)
                    st.session_state.embeddings = embeddings

                    with st.spinner("Building FAISS index..."):
                        store = build_index(embeddings, chunks)
                    st.session_state.store = store
                except VectorStoreError as exc:
                    st.session_state.processing_errors.append(f"FAISS indexing failed: {exc}")
                except Exception as exc:  # noqa: BLE001 - surface any embedding failure to the user
                    st.session_state.processing_errors.append(
                        f"Embedding generation failed: {exc}"
                    )

        st.session_state.doc_signature = signature

for error in st.session_state.processing_errors:
    st.warning(error)

# --------------------------------------------------------------------------
# KPI dashboard
# --------------------------------------------------------------------------
pages = st.session_state.pages
chunks = st.session_state.chunks
store = st.session_state.store

total_chars = sum(len(p.page_text) for p in pages)
total_tokens = sum(c.token_count for c in chunks)
avg_tokens_per_chunk = (total_tokens / len(chunks)) if chunks else 0.0
embedding_dim = get_embedding_dimension() if store is not None else None
pdf_count = len({p.file_name for p in pages})
latest_qa = st.session_state.qa_history[-1] if st.session_state.qa_history else None

kpi_cols = st.columns(7)
kpi_cols[0].metric("PDFs uploaded", pdf_count)
kpi_cols[1].metric("Pages processed", len(pages))
kpi_cols[2].metric("Chunks generated", len(chunks))
kpi_cols[3].metric("Total tokens", total_tokens)
kpi_cols[4].metric("Embedding dim", embedding_dim if embedding_dim else "—")
kpi_cols[5].metric("Retrieved chunks", len(latest_qa["results"]) if latest_qa else 0)
kpi_cols[6].metric(
    "Last latency (s)", f"{latest_qa['total_latency']:.2f}" if latest_qa else "—"
)

st.divider()

tabs = st.tabs(
    ["Q&A", "PDF Processing", "Chunking", "Embeddings", "Retrieval", "Evaluation", "Data Preview"]
)

# --------------------------------------------------------------------------
# Q&A tab
# --------------------------------------------------------------------------
with tabs[0]:
    st.subheader("Ask a question")
    question = st.text_input("Your question", key="question_input")
    ask_clicked = st.button("Ask", type="primary")

    if ask_clicked:
        if not question or not question.strip():
            st.warning("Please enter a question.")
        elif store is None:
            st.warning("Please upload and process at least one PDF first.")
        else:
            question_tokens = count_tokens_approx(question)
            results, retrieval_latency = retrieve(
                question, store, top_k=top_k, score_threshold=score_threshold
            )
            context_tokens = sum(count_tokens_approx(r.text) for r in results)
            if not results:
                st.info("No relevant chunks were retrieved for this question.")

            rag_answer = generate_answer(question, results)
            eval_result = evaluate(
                question, rag_answer.answer, results, retrieval_latency, rag_answer.latency_seconds
            )
            st.session_state.qa_history.append(
                {
                    "question": question,
                    "question_tokens": question_tokens,
                    "context_tokens": context_tokens,
                    "results": results,
                    "retrieval_latency": retrieval_latency,
                    "answer": rag_answer,
                    "eval": eval_result,
                    "total_latency": retrieval_latency + rag_answer.latency_seconds,
                }
            )
            latest_qa = st.session_state.qa_history[-1]

    if latest_qa:
        st.markdown("### Answer")
        if latest_qa["answer"].error:
            st.error(latest_qa["answer"].error)
        else:
            st.write(latest_qa["answer"].answer)

            token_cols = st.columns(4)
            token_cols[0].metric("Question tokens", latest_qa["question_tokens"])
            token_cols[1].metric("Context tokens", latest_qa["context_tokens"])
            token_cols[2].metric("Answer tokens", latest_qa["answer"].answer_token_count)
            token_cols[3].metric("Response latency (s)", f"{latest_qa['answer'].latency_seconds:.2f}")

            st.markdown("### Source citations")
            if latest_qa["results"]:
                for result in latest_qa["results"]:
                    st.markdown(
                        f"- **{result.source_file}**, page {result.page_number} "
                        f"(score: {result.score:.3f})"
                    )
            else:
                st.caption(
                    "No sources — the answer above is the documents-insufficient fallback message."
                )
    else:
        st.caption("Ask a question after processing your documents to see the grounded answer here.")

# --------------------------------------------------------------------------
# PDF Processing tab
# --------------------------------------------------------------------------
with tabs[1]:
    st.subheader("PDF Processing")
    if not pages:
        st.caption("No PDFs processed yet.")
    else:
        df = pd.DataFrame(
            [
                {
                    "File": p.file_name,
                    "Page": p.page_number,
                    "Characters": len(p.page_text),
                    "Empty/Scanned": p.is_empty,
                }
                for p in pages
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric("Total extracted characters", total_chars)

# --------------------------------------------------------------------------
# Chunking tab
# --------------------------------------------------------------------------
with tabs[2]:
    st.subheader("Chunking")
    if not chunks:
        st.caption("No chunks generated yet.")
    else:
        df = pd.DataFrame(
            [
                {
                    "Chunk ID": c.chunk_id,
                    "PDF": c.source_file,
                    "Page": c.page_number,
                    "Token Count": c.token_count,
                    "Chunk Preview": (c.text[:120] + "…") if len(c.text) > 120 else c.text,
                }
                for c in chunks
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total chunks", len(chunks))
        col2.metric("Total tokens", total_tokens)
        col3.metric("Avg tokens/chunk", f"{avg_tokens_per_chunk:.1f}")

# --------------------------------------------------------------------------
# Embeddings tab
# --------------------------------------------------------------------------
with tabs[3]:
    st.subheader("Embeddings")
    if store is None:
        st.caption("No embeddings generated yet.")
    else:
        st.metric("Embedding dimension", embedding_dim)
        st.caption(
            "Full vectors are never displayed. First 8 values of the first chunk's "
            "embedding, shown only for demonstration:"
        )
        preview_values = st.session_state.embeddings[0][:8]
        st.code(", ".join(f"{value:.4f}" for value in preview_values))

# --------------------------------------------------------------------------
# Retrieval tab
# --------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Retrieval")
    if not latest_qa:
        st.caption("Ask a question in the Q&A tab to see retrieval details here.")
    else:
        st.write(f"**Query:** {latest_qa['question']}")
        st.write(f"**Retrieval latency:** {latest_qa['retrieval_latency']:.3f}s")
        if latest_qa["results"]:
            df = pd.DataFrame(
                [
                    {
                        "Chunk ID": r.chunk_id,
                        "Score": round(r.score, 4),
                        "Source PDF": r.source_file,
                        "Page": r.page_number,
                        "Preview": (r.text[:120] + "…") if len(r.text) > 120 else r.text,
                    }
                    for r in latest_qa["results"]
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No chunks were retrieved for the last question.")

# --------------------------------------------------------------------------
# Evaluation tab
# --------------------------------------------------------------------------
with tabs[5]:
    st.subheader("Evaluation")
    st.caption(
        "Relevance/groundedness metrics below are heuristic (embedding-similarity based), "
        "not exact ground truth."
    )
    if not latest_qa:
        st.caption("Ask a question in the Q&A tab to see evaluation metrics here.")
    else:
        ev = latest_qa["eval"]
        cols = st.columns(4)
        cols[0].metric(
            "Context relevance (heuristic)",
            f"{ev.context_relevance:.3f}" if ev.context_relevance is not None else "—",
        )
        cols[1].metric(
            "Answer relevance (heuristic)",
            f"{ev.answer_relevance:.3f}" if ev.answer_relevance is not None else "—",
        )
        cols[2].metric(
            "Groundedness (heuristic)",
            f"{ev.groundedness:.3f}" if ev.groundedness is not None else "—",
        )
        cols[3].metric("Source coverage", f"{ev.source_coverage:.3f}")

        latency_cols = st.columns(2)
        latency_cols[0].metric("Retrieval latency (s)", f"{ev.retrieval_latency_seconds:.3f}")
        latency_cols[1].metric("Response latency (s)", f"{ev.response_latency_seconds:.3f}")

        st.divider()
        st.markdown("#### Recall / Precision@K")
        st.caption("Requires a ground-truth CSV uploaded in the sidebar.")
        if ground_truth_file is not None:
            gt_df = pd.read_csv(ground_truth_file)
            match = gt_df[gt_df["question"].astype(str).str.strip() == latest_qa["question"].strip()]
            if match.empty:
                st.info("No ground-truth row matches the last question.")
            else:
                relevant_ids = [
                    cid.strip()
                    for cid in str(match.iloc[0]["relevant_chunk_ids"]).split(";")
                    if cid.strip()
                ]
                retrieved_ids = [r.chunk_id for r in latest_qa["results"]]
                recall_result = recall_at_k(retrieved_ids, relevant_ids)
                precision = precision_at_k(retrieved_ids, relevant_ids)

                recall_cols = st.columns(2)
                recall_cols[0].metric("Recall@K", f"{recall_result.recall_at_k:.3f}")
                recall_cols[1].metric("Precision@K", f"{precision:.3f}")
                st.write("Retrieved relevant chunks:", recall_result.retrieved_relevant or "—")
                st.write("Missed relevant chunks:", recall_result.missed_relevant or "—")
        else:
            st.caption("No ground-truth file uploaded — Recall@K / Precision@K unavailable.")

# --------------------------------------------------------------------------
# Data Preview tab
# --------------------------------------------------------------------------
with tabs[6]:
    st.subheader("Data Preview")
    if not chunks:
        st.caption("No data yet — process your PDFs first.")
    else:
        preview_df = pd.DataFrame(
            [
                {"Chunk ID": c.chunk_id, "Source": c.source_file, "Page": c.page_number, "Text": c.text}
                for c in chunks
            ]
        )
        st.dataframe(preview_df, use_container_width=True, height=400)
