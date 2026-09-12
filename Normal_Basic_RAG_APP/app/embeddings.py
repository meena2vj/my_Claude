"""Sentence-transformer embeddings, loaded once and cached by Streamlit."""

import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL


@st.cache_resource(show_spinner="Loading embedding model...")
def load_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    model: SentenceTransformer | None = None,
    batch_size: int = 32,
) -> np.ndarray:
    """Batch-encode texts into L2-normalized float32 embeddings."""
    model = model or load_embedding_model()
    if not texts:
        return np.zeros((0, model.get_embedding_dimension()), dtype="float32")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(embeddings, dtype="float32")


def get_embedding_dimension(model: SentenceTransformer | None = None) -> int:
    model = model or load_embedding_model()
    return model.get_embedding_dimension()
