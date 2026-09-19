"""Cached sentence-transformer embedding model used by the RAG layer."""

import streamlit as st
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL


@st.cache_resource(show_spinner="Loading embedding model...")
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]):
    model = get_embedding_model()
    return model.encode(texts, normalize_embeddings=True)
