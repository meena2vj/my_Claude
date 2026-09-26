"""Central configuration: env loading and constants. Never hard-code secrets here."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# --- LLM (OpenRouter) ---
OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY: str | None = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL: str = os.environ.get("OPENROUTER_MODEL", "openai/gpt-oss-120b")
GENERATION_TEMPERATURE: float = 0.15
GENERATION_MAX_TOKENS: int = 1024

# --- Optional Langfuse tracing ---
LANGFUSE_PUBLIC_KEY: str | None = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY: str | None = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST: str = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
LANGFUSE_ENABLED: bool = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

# --- Guardrail limits ---
MAX_UPLOAD_FILE_SIZE_MB: int = int(os.environ.get("MAX_UPLOAD_FILE_SIZE_MB", "25"))
MAX_BUSINESS_CONTEXT_FILE_SIZE_MB: int = int(os.environ.get("MAX_BUSINESS_CONTEXT_FILE_SIZE_MB", "15"))
ALLOWED_DATA_EXTENSIONS: tuple[str, ...] = tuple(
    os.environ.get("ALLOWED_DATA_EXTENSIONS", ".csv,.xlsx").split(",")
)
ALLOWED_CONTEXT_EXTENSIONS: tuple[str, ...] = tuple(
    os.environ.get("ALLOWED_CONTEXT_EXTENSIONS", ".pdf,.txt").split(",")
)
MAX_ANALYST_RETRIES: int = 2
SHORT_TERM_MEMORY_TURNS: int = 6  # last N ChatTurns (~3 exchanges) fed back into the analyst prompt

# --- RAG business-context layer ---
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 120
RAG_TOP_K: int = 5

# --- Observability ---
ENABLE_METRICS_SERVER: bool = os.environ.get("ENABLE_METRICS_SERVER", "false").lower() == "true"
METRICS_SERVER_PORT: int = int(os.environ.get("METRICS_SERVER_PORT", "9108"))
OTEL_EXPORTER_OTLP_ENDPOINT: str | None = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or None

# --- Storage paths ---
TRACE_DB_PATH: Path = PROJECT_ROOT / os.environ.get("TRACE_DB_PATH", "data/db/traces.sqlite")
MEMORY_DB_PATH: Path = PROJECT_ROOT / os.environ.get("MEMORY_DB_PATH", "data/db/memory.sqlite")
UPLOAD_DIR: Path = PROJECT_ROOT / "data" / "uploads"
BUSINESS_CONTEXT_DIR: Path = PROJECT_ROOT / "data" / "business_context"
REPORTS_DIR: Path = PROJECT_ROOT / "reports" / "generated"

INSUFFICIENT_CONTEXT_MESSAGE: str = (
    "The available data and business context do not support a confident answer."
)
