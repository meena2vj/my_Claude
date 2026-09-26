# Vision RAG

Multi-document Vision RAG question-answering app: OCR-based image/PDF ingestion, hybrid dense+BM25 retrieval fused with Reciprocal Rank Fusion (RRF), grounded generation via Groq with citations, prompt-injection and OCR-junk guardrails, and a retrieval/answer evaluation framework. See [CLAUDE.md](CLAUDE.md) for the full spec.

## Setup

```bash
cd Vision_RAG
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set GROQ_API_KEY
```

## Run

```bash
source .venv/bin/activate
streamlit run app.py --server.port 8503
```

Open http://localhost:8503

## Test

```bash
source .venv/bin/activate
pytest -q
```

## Notes

- OCR uses [EasyOCR](https://github.com/JaidedAI/EasyOCR) (no system `tesseract` dependency required). The first run downloads its model weights.
- CLIP embeddings are opt-in via `ENABLE_CLIP_EMBEDDINGS=true` in `.env` (uses `sentence-transformers`' `clip-ViT-B-32`).
- Without `GROQ_API_KEY` set, retrieval and evaluation still work; answer generation returns an explicit error instead of calling the LLM.
