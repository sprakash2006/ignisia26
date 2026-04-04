"""
Embedding service — generates vector embeddings for text chunks.
Uses sentence-transformers with the same model as the original pipeline.
"""

from sentence_transformers import SentenceTransformer
from config import settings

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    model = get_model()
    return model.encode(text).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts."""
    model = get_model()
    return model.encode(texts).tolist()
