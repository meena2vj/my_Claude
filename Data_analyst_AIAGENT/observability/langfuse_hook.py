"""Optional Langfuse tracing -- import-guarded and env-var-gated. When not
configured (no keys, or the `langfuse` package missing), every function is a
no-op so the rest of the app never has to branch on whether Langfuse is
enabled, and a Langfuse outage can never break a node.
"""

from config.logging_config import get_logger
from config.settings import LANGFUSE_ENABLED, LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

logger = get_logger(__name__)

_client = None

if LANGFUSE_ENABLED:
    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY, secret_key=LANGFUSE_SECRET_KEY, host=LANGFUSE_HOST
        )
    except ImportError:
        logger.warning("LANGFUSE_PUBLIC_KEY/SECRET_KEY are set but the langfuse package is not "
                        "installed; Langfuse tracing is disabled.")
        _client = None


def is_enabled() -> bool:
    return _client is not None


def log_llm_call(
    *, trace_id: str, node: str, model: str, input_text: str, output_text: str | None, ok: bool
) -> None:
    if _client is None:
        return
    try:
        span = _client.trace(id=trace_id, name=node)
        span.generation(
            name=f"{node}_llm_call",
            model=model,
            input=input_text,
            output=output_text,
            metadata={"ok": ok},
        )
    except Exception:  # noqa: BLE001 - optional tracing must never break a node
        logger.exception("langfuse_log_failed")
