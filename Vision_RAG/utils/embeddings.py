"""Sentence-transformer text embeddings, plus optional CLIP image embeddings.

Both loaded once and cached by Streamlit. CLIP support reuses the
sentence-transformers `clip-ViT-B-32` wrapper — no extra heavy dependency —
and is only invoked when `ENABLE_CLIP_EMBEDDINGS` is true, per CLAUDE.md's
"CLIP embeddings: available for multimodal similarity support" (available,
not mandatory-on).
"""

import numpy as np
import streamlit as st
from PIL import Image
from sentence_transformers import SentenceTransformer

from config import CLIP_MODEL, EMBEDDING_MODEL


@st.cache_resource(show_spinner="Loading embedding model...")
def load_embedding_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)


@st.cache_resource(show_spinner="Loading CLIP model...")
def load_clip_model(model_name: str = CLIP_MODEL) -> SentenceTransformer:
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    model: SentenceTransformer | None = None,
    batch_size: int = 32,
) -> np.ndarray:
    """Batch-encode texts into L2-normalized float32 embeddings."""
    model = model or load_embedding_model()
    if not texts:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype="float32")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(embeddings, dtype="float32")


def embed_images_clip(
    images: list[Image.Image],
    model: SentenceTransformer | None = None,
) -> np.ndarray:
    """Batch-encode PIL images into L2-normalized CLIP embeddings, for optional
    visual-similarity retrieval alongside text search. Only called when
    `ENABLE_CLIP_EMBEDDINGS` is true."""
    model = model or load_clip_model()
    if not images:
        return np.zeros((0, model.get_sentence_embedding_dimension()), dtype="float32")

    embeddings = model.encode(
        images,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    return np.asarray(embeddings, dtype="float32")


def get_embedding_dimension(model: SentenceTransformer | None = None) -> int:
    model = model or load_embedding_model()
    return model.get_sentence_embedding_dimension()
