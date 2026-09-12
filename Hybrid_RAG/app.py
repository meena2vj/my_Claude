"""Streamlit UI for the Multi-PDF Hybrid RAG Q&A system (dense + sparse + RRF)."""

import pandas as pd
import streamlit as st

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    GROQ_API_KEY,
    RETRIEVAL_MODE_DEFAULT,
    RETRIEVAL_MODES,
    RRF_K_DEFAULT,
    TOP_K_DEFAULT,
    TOP_K_MAX,
    TOP_K_MIN,
)
from src.hybrid.fusion import retrieve
from src.hybrid.guardrails import scan_chunks
from src.ingestion.chunking import chunk_pages
from src.ingestion.pdf_processor import process_uploaded_pdfs
from src.llm.rag_chain import generate_answer
from src.retrieval.dense import VectorStoreError, build_dense_index
from src.retrieval.embeddings import embed_texts, get_embedding_dimension, load_embedding_model
from src.retrieval.sparse import BM25IndexError, build_bm25_index
from src.utils.helpers import audit_log, count_tokens_approx, read_audit_log

st.set_page_config(page_title="Multi-PDF Hybrid RAG", page_icon="🔎", layout="wide")

st.markdown(
    """
    <div style="padding: 1.25rem 1.5rem; border-radius: 12px;
                background: linear-gradient(135deg, #f5f8ff 0%, #eef2fb 100%);
                border: 1px solid #dbe3f3; margin-bottom: 1rem;">
        <h1 style="margin:0; color:#1f2a44; font-size:1.9rem;">Multi-PDF Hybrid RAG</h1>
        <p style="margin:0.25rem 0 0 0; color:#5b6478; font-size:0.95rem;">
            Dense (FAISS + MiniLM) + Sparse (BM25) retrieval fused with RRF, answered
            with citations and guardrails against prompt injection.
        </p>
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
    "dense_store": None,
    "bm25_store": None,
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
    retrieval_mode = st.selectbox(
        "Retrieval mode", RETRIEVAL_MODES, index=RETRIEVAL_MODES.index(RETRIEVAL_MODE_DEFAULT)
    )
    rrf_k = st.slider(
        "RRF k (damping constant)", 10, 100, RRF_K_DEFAULT, step=5,
        disabled=retrieval_mode != "hybrid",
    )

    st.divider()
    if GROQ_API_KEY:
        st.success("Groq API key detected")
    else:
        st.error("GROQ_API_KEY missing — set it in .env to enable answer generation")

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
        st.session_state.dense_store = None
        st.session_state.bm25_store = None

        if not pages:
            st.session_state.processing_errors.append("No pages could be extracted from the uploaded PDFs.")
        else:
            with st.spinner("Chunking text..."):
                chunks = chunk_pages(pages, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

            if not chunks:
                st.session_state.processing_errors.append(
                    "No extractable text was found in the uploaded PDFs "
                    "(they may be scanned images without OCR text)."
                )
            else:
                with st.spinner("Scanning content for prompt-injection attempts..."):
                    chunks = scan_chunks(chunks)
                suspicious_count = sum(1 for c in chunks if c.is_suspicious)
                if suspicious_count:
                    st.session_state.processing_errors.append(
                        f"{suspicious_count} chunk(s) were flagged as containing suspicious "
                        "instruction-like text and will be excluded from grounded answers."
                    )

                st.session_state.chunks = chunks
                try:
                    with st.spinner("Generating embeddings + building FAISS index..."):
                        model = load_embedding_model()
                        embeddings = embed_texts([c.text for c in chunks], model=model)
                        dense_store = build_dense_index(embeddings, chunks)
                    st.session_state.dense_store = dense_store

                    with st.spinner("Building BM25 sparse index..."):
                        bm25_store = build_bm25_index(chunks)
                    st.session_state.bm25_store = bm25_store
                except (VectorStoreError, BM25IndexError) as exc:
                    st.session_state.processing_errors.append(f"Indexing failed: {exc}")
                except Exception as exc:  # noqa: BLE001 - surface any embedding failure to the user
                    st.session_state.processing_errors.append(f"Embedding generation failed: {exc}")

        st.session_state.doc_signature = signature
        audit_log(
            "documents_processed",
            {
                "file_count": len({p.file_name for p in st.session_state.pages}),
                "chunk_count": len(st.session_state.chunks),
            },
        )

for error in st.session_state.processing_errors:
    st.warning(error)

# --------------------------------------------------------------------------
# KPI dashboard
# --------------------------------------------------------------------------
pages = st.session_state.pages
chunks = st.session_state.chunks
dense_store = st.session_state.dense_store
bm25_store = st.session_state.bm25_store

total_tokens = sum(c.token_count for c in chunks)
embedding_dim = get_embedding_dimension() if dense_store is not None else None
pdf_count = len({p.file_name for p in pages})
suspicious_total = sum(1 for c in chunks if c.is_suspicious)
latest_qa = st.session_state.qa_history[-1] if st.session_state.qa_history else None

kpi_cols = st.columns(6)
kpi_cols[0].metric("PDFs uploaded", pdf_count)
kpi_cols[1].metric("Pages processed", len(pages))
kpi_cols[2].metric("Chunks generated", len(chunks))
kpi_cols[3].metric("Flagged chunks", suspicious_total)
kpi_cols[4].metric("Embedding dim", embedding_dim if embedding_dim else "—")
kpi_cols[5].metric("Last latency (s)", f"{latest_qa['total_latency']:.2f}" if latest_qa else "—")

st.divider()

tabs = st.tabs(["Q&A", "Retrieval Detail", "PDF Processing", "Chunking", "Audit Trail"])

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
        elif dense_store is None and bm25_store is None:
            st.warning("Please upload and process at least one PDF first.")
        else:
            question_tokens = count_tokens_approx(question)
            results = retrieve(question, retrieval_mode, dense_store, bm25_store, top_k, rrf_k=rrf_k)
            context_tokens = sum(count_tokens_approx(r.text) for r in results if not r.is_suspicious)
            if not results:
                st.info("No relevant chunks were retrieved for this question.")

            rag_answer = generate_answer(question, results, retrieval_mode=retrieval_mode)
            st.session_state.qa_history.append(
                {
                    "question": question,
                    "question_tokens": question_tokens,
                    "context_tokens": context_tokens,
                    "results": results,
                    "mode": retrieval_mode,
                    "answer": rag_answer,
                    "total_latency": rag_answer.latency_seconds,
                }
            )
            latest_qa = st.session_state.qa_history[-1]

    if latest_qa:
        st.markdown("### Answer")
        if latest_qa["answer"].flagged:
            st.error("⚠️ Potential prompt injection detected — request was refused. " + latest_qa["answer"].answer)
        elif latest_qa["answer"].error:
            st.error(latest_qa["answer"].error)
        else:
            st.write(latest_qa["answer"].answer)

            token_cols = st.columns(4)
            token_cols[0].metric("Question tokens", latest_qa["question_tokens"])
            token_cols[1].metric("Context tokens", latest_qa["context_tokens"])
            token_cols[2].metric("Answer tokens", latest_qa["answer"].answer_token_count)
            token_cols[3].metric("Response latency (s)", f"{latest_qa['answer'].latency_seconds:.2f}")

            st.markdown("### Source citations")
            trusted = [r for r in latest_qa["results"] if not r.is_suspicious]
            flagged = [r for r in latest_qa["results"] if r.is_suspicious]
            if trusted:
                for r in trusted:
                    st.markdown(
                        f"- **{r.source_file}**, page {r.page_number} "
                        f"(fused score: {r.fused_score:.4f}"
                        + (f", dense rank {r.dense_rank}" if r.dense_rank else "")
                        + (f", sparse rank {r.sparse_rank}" if r.sparse_rank else "")
                        + ")"
                    )
            else:
                st.caption("No trusted sources — the answer above is the documents-insufficient fallback message.")
            if flagged:
                st.warning(
                    f"{len(flagged)} retrieved chunk(s) were excluded as suspicious "
                    f"(sources: {', '.join(sorted({r.source_file for r in flagged}))})."
                )
    else:
        st.caption("Ask a question after processing your documents to see the grounded answer here.")

# --------------------------------------------------------------------------
# Retrieval Detail tab
# --------------------------------------------------------------------------
with tabs[1]:
    st.subheader("Retrieval Detail")
    if not latest_qa:
        st.caption("Ask a question in the Q&A tab to see retrieval details here.")
    else:
        st.write(f"**Query:** {latest_qa['question']}  |  **Mode:** {latest_qa['mode']}")
        if latest_qa["results"]:
            df = pd.DataFrame(
                [
                    {
                        "Chunk ID": r.chunk_id,
                        "Fused Score": round(r.fused_score, 4),
                        "Dense Rank": r.dense_rank,
                        "Sparse Rank": r.sparse_rank,
                        "Source PDF": r.source_file,
                        "Page": r.page_number,
                        "Suspicious": r.is_suspicious,
                        "Preview": (r.text[:120] + "…") if len(r.text) > 120 else r.text,
                    }
                    for r in latest_qa["results"]
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No chunks were retrieved for the last question.")

# --------------------------------------------------------------------------
# PDF Processing tab
# --------------------------------------------------------------------------
with tabs[2]:
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

# --------------------------------------------------------------------------
# Chunking tab
# --------------------------------------------------------------------------
with tabs[3]:
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
                    "Suspicious": c.is_suspicious,
                    "Chunk Preview": (c.text[:120] + "…") if len(c.text) > 120 else c.text,
                }
                for c in chunks
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total chunks", len(chunks))
        col2.metric("Total tokens", total_tokens)
        col3.metric("Flagged chunks", suspicious_total)

# --------------------------------------------------------------------------
# Audit Trail tab
# --------------------------------------------------------------------------
with tabs[4]:
    st.subheader("Audit Trail")
    st.caption("Local, append-only log of uploads, retrieval requests, answers, and guardrail events.")
    events = read_audit_log(limit=100)
    if not events:
        st.caption("No audit events logged yet.")
    else:
        df = pd.DataFrame(events)
        st.dataframe(df, use_container_width=True, hide_index=True)
