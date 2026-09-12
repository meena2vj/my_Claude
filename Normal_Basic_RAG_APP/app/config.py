"""Central configuration and constants for the Multi-PDF RAG Q&A app."""

import os

from dotenv import load_dotenv

load_dotenv()

# --- Chunking (configurable from sidebar) ---
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 120

# --- Embeddings ---
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

# --- Retrieval ---
TOP_K_DEFAULT: int = 5
TOP_K_MIN: int = 1
TOP_K_MAX: int = 20
SCORE_THRESHOLD_DEFAULT: float = 0.0  # 0 = no filtering, prefer recall

# --- Generation ---
# Generation runs on Groq (OpenAI-compatible chat completions API).
# openai/gpt-oss-120b supports `temperature`, satisfying this project's
# "temperature: 0.1-0.2, deterministic where possible" requirement.
GROQ_MODEL: str = "openai/gpt-oss-120b"
GENERATION_TEMPERATURE: float = 0.15
GENERATION_MAX_TOKENS: int = 1024

GROQ_API_KEY: str | None = os.environ.get("GROQ_API_KEY")

INSUFFICIENT_CONTEXT_MESSAGE: str = (
    "The uploaded documents do not contain enough information to answer this confidently."
)

SYSTEM_PROMPT: str = (
    "You are a document-grounded RAG assistant. "
    "Use only the supplied context to answer the question. "
    "Never invent facts that are not present in the context. "
    "Mention uncertainty clearly when the context is incomplete. "
    "Cite the source PDF file name and page number for every claim. "
    "Prefer direct, concise, but complete answers. "
    f'If the context is insufficient to answer, respond exactly with: "{INSUFFICIENT_CONTEXT_MESSAGE}"'
)

# --- File handling ---
ALLOWED_EXTENSIONS: tuple[str, ...] = (".pdf",)
