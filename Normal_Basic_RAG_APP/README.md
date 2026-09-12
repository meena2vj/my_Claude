# Multi-PDF RAG Q&A

A local, professional Streamlit app for asking grounded questions over multiple PDFs, with full retrieval and evaluation transparency.

## Features

- Upload and process multiple PDFs (text extraction via PyMuPDF, with per-page metadata for citations)
- Fixed-length chunking (LangChain `CharacterTextSplitter`, configurable size/overlap)
- Local embeddings via `sentence-transformers/all-MiniLM-L6-v2`, cached across reruns
- FAISS similarity search with configurable top-k and optional score threshold
- Grounded answer generation via Groq (`openai/gpt-oss-120b`) — answers only from retrieved context, with an explicit "insufficient information" fallback and source citations (file + page)
- Full transparency: token counts, per-chunk previews, retrieval scores, response latency
- Lightweight RAG evaluation: heuristic context relevance / answer relevance / groundedness / source coverage, plus exact Recall@K / Precision@K when a ground-truth CSV is supplied

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in GROQ_API_KEY
```

## Run

```bash
streamlit run app/app.py
```

The app opens at `http://localhost:8501`.

## Usage

1. Upload one or more PDFs in the sidebar/upload area and click **Process Documents**.
2. Review the **PDF Processing**, **Chunking**, and **Embeddings** tabs to confirm extraction, chunking, and vectorization.
3. Ask a question in the **Q&A** tab. The answer is generated only from retrieved chunks and cites the source PDF and page.
4. Inspect the **Retrieval** tab for per-query similarity scores and latency, and the **Evaluation** tab for heuristic RAG metrics (and exact recall/precision if you upload a ground-truth CSV with `question` and `relevant_chunk_ids` columns).

## Tests

```bash
pytest app/tests/
```

## Project Structure

See `CLAUDE.md` for the full specification this app implements.
