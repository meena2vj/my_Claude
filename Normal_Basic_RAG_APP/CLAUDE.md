CLAUDE.md — Multi-PDF RAG Q&A
1. Project Goal
Build a professional local Multi-PDF RAG Question Answering System where users can upload multiple PDFs, process them, retrieve relevant chunks, and ask grounded questions.
2. Tech Stack
IDE: VS Code
AI Coding Assistant: Claude Code
Language: Python 3.11+
UI: Streamlit
PDF Processing: PyMuPDF (fitz)
Chunking: Fixed Length
Tokenization: word level
Embeddings: sentence-transformers/all-MiniLM-L6-v2
Vector DB: FAISS
RAG Framework: LangChain
Retrieval and Generation Evaluation Metrics
Testing: Pytest
Deployment: Local Streamlit
3. Core Flow
Upload multiple PDFs
Extract text with PyMuPDF
Clean and normalize text
Split into chunks
Count/display tokens
Generate embeddings
Store embeddings in FAISS
Accept user question
Embed question
Retrieve top-k relevant chunks
Generate answer using retrieved context only
Show sources, retrieval details, latency, and evaluation metrics
4. Required Project Structure
app/
├── app.py
├── config.py
├── pdf_processor.py
├── chunking.py
├── embeddings.py
├── vector_store.py
├── retriever.py
├── rag_chain.py
├── evaluator.py
├── utils.py
└── tests/
    ├── test_pdf_processor.py
    ├── test_chunking.py
    ├── test_retriever.py
    └── test_rag_chain.py
requirements.txt
.env.example
README.md
CLAUDE.md

6. PDF Processing
Support multiple PDF uploads.
Use PyMuPDF only.
Extract:
file name
page number
page text
Preserve source metadata for citations.
Handle empty/scanned pages safely.
Do not crash if one PDF fails.

7. Chunking
Use LangChain text splitting.
Recommended defaults:
chunk_size: 800
chunk_overlap: 120
configurable from sidebar
For every chunk store:
chunk_id
source_file
page_number
text
token_count
8. Token Tracking
Show:
total extracted characters
total chunks
total tokens
average tokens/chunk
question token count
retrieved context token count
answer token count when available
Use a lightweight tokenizer approximation if model tokenizer is unavailable.
9. Embeddings
Model:
sentence-transformers/all-MiniLM-L6-v2
Requirements:
load once using Streamlit cache
batch embeddings
normalize embeddings when appropriate
display embedding dimension
never expose full vectors in UI
optionally show first 5–10 values for demonstration
10. Vector Database
Use FAISS.
create index after document processing
persist only if explicitly implemented
support rebuilding index
map FAISS results back to source metadata
11. Retrieval
Primary goal: high recall.
Implement:
similarity search
configurable top_k
default top_k: 5
optional score threshold
retrieval score display
source + page display
Prefer recall over overly aggressive filtering.
12. RAG Generation

Generation rules:
answer only from retrieved context
do not fabricate missing facts
if context is insufficient, say:
"The uploaded documents do not contain enough information to answer this confidently."
provide source file and page references
keep responses concise but complete
preserve factual grounding
Recommended generation settings:
temperature: 0.1–0.2
deterministic where possible
reasonable max output tokens

13. Prompt Template
System behavior:
You are a document-grounded RAG assistant.
Use only supplied context.
Never invent facts.
Mention uncertainty clearly.
Cite source PDF and page.
Prefer direct answers.
Prompt inputs:
context
question
source metadata
14. Streamlit UI
Build an extremely professional light-color UI/UX.
Must include:
header/title: Multi-PDF RAG Q&A
moving line/ticker: PDF Q and A
upload area
process button
sidebar configuration
question input
answer panel
source citations
retrieval panel
evaluation panel
15. Dashboard Sections
Show KPI cards for:
PDFs uploaded
pages processed
chunks generated
total tokens
embedding dimension
retrieved chunks
response latency
Tabs:
Q&A
PDF Processing
Chunking
Embeddings
Retrieval
Evaluation
Data Preview
16. Chunking Output
Display table:
Chunk ID
PDF
Page
Token Count
Chunk Preview
17. Retrieval Output
For every question show:
query
retrieved chunks
similarity score
source PDF
page number
chunk preview
retrieval latency
18. Evaluation Metrics
Implement lightweight RAG evaluation:
Retrieval Recall
Precision@K when reference data exists
Context Relevance
Answer Relevance
Groundedness/Faithfulness
Source Coverage
Response Latency
If ground-truth answers are unavailable:
clearly mark heuristic/LLM-based metrics
never present estimated metrics as exact truth
19. Recall Evaluation
For test datasets with expected source chunks:
Recall = Relevant Retrieved / Total Relevant
Display:
Recall@K
retrieved relevant chunks
missed relevant chunks
20. Error Handling
Handle:
invalid PDFs
empty PDFs
no extracted text
missing API key
embedding failure
FAISS failure
empty question
no relevant retrieval
Show user-friendly messages.
21. Performance Rules
cache embedding model
cache processed resources when safe
avoid embedding unchanged PDFs repeatedly
avoid unnecessary LLM calls
separate ingestion from Q&A
show progress during processing
22. Code Quality
modular Python
type hints
concise docstrings
small reusable functions
no giant files
no duplicated logic
no hardcoded secrets
use config/constants
follow PEP8
23. Testing
Use Pytest.
Test:
PDF text extraction
metadata preservation
chunk overlap
token counting
embedding shape
FAISS indexing
top-k retrieval
recall calculation
empty inputs
RAG prompt construction
graceful API failure
24. Security
process PDFs locally
do not log sensitive PDF text unnecessarily
never expose API key
validate uploaded file types
use safe temporary file handling
25. Deployment
Run locally:
pip install -r requirements.txt
streamlit run app/app.py
26. Claude Code Instructions
When implementing:
build phase by phase
do not rewrite working modules unnecessarily
inspect existing files before editing
keep architecture modular
run tests after important changes
fix root causes, not symptoms
preserve source metadata end-to-end
ensure UI remains light, clean, aligned, and professional
never remove evaluation or retrieval transparency features
27. Definition of Done
Project is complete when:
multiple PDFs upload successfully
text/chunks/tokens are visible
embeddings + FAISS work
user can ask questions
answers are grounded in retrieved chunks
citations show PDF + page
retrieval scores are visible
recall/evaluation metrics are visible
Pytest passes
Streamlit runs locally
UI is polished, light, responsive, and professional
