# Multi-PDF Hybrid RAG

Local, multi-PDF question answering with dense (FAISS + MiniLM) and sparse (BM25) retrieval
fused via Reciprocal Rank Fusion (RRF), answered by Groq (`openai/gpt-oss-120b`) grounded
strictly in retrieved chunks, with prompt-injection guardrails and a local audit trail.

## Launch (local only)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then add your GROQ_API_KEY
streamlit run app.py
```

The app opens at **http://localhost:8501**. This project is local-only by design — there is
no external/public deployment. PDF content, embeddings, and the audit log all stay on your
machine. Retrieval (dense, sparse, hybrid) works fully offline; only answer generation calls
the Groq API and requires `GROQ_API_KEY`.

## Architecture

Upload PDFs → PyMuPDF extraction → chunking → guardrail scan (flags suspicious chunk content)
→ MiniLM embeddings → FAISS dense index + BM25 sparse index → query fused with RRF → grounded
Groq answer with citations, refused/flagged if the query itself looks like an injection attempt.

## Tests & evaluation report

```bash
pytest tests/ -v
python scripts/run_evaluation.py
```

`scripts/run_evaluation.py` builds a small synthetic corpus with known relevant chunks per
query and prints a dense vs. sparse vs. hybrid Recall@k / MRR / NDCG@k / HitRate comparison —
this is the retrieval evaluation referenced in `CLAUDE.md`'s Evaluation section.
