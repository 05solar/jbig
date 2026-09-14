# 챗봇·OCR·가이드가 공용으로 쓰는 임베딩 provider(local/openai/none) 서비스를 담당하는 파일
"""Shared embedding service for RAG indexing and search.

One provider per process (lazy singleton): the chatbot and the OCR document
review must never load their own models. On any provider failure embed_texts
returns None so callers fall back to lexical-only search instead of crashing.
"""
from __future__ import annotations

import logging
import os
import threading
import time

from ..core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_local_model = None
_local_failed = False
_load_seconds: float | None = None


def signature() -> str:
    """Identifies provider+model; stored in embedding_model and used in cache keys."""
    provider = settings.rag_embedding_provider
    if provider == "local":
        return f"local:{settings.rag_local_embedding_model.split('/')[-1]}"
    if provider == "openai":
        return f"openai:{settings.embedding_model}"
    return "none"


def _get_local_model():
    global _local_model, _local_failed, _load_seconds
    with _lock:
        if _local_model is not None or _local_failed:
            return _local_model
        try:
            if settings.rag_model_cache_dir:
                os.environ.setdefault("HF_HOME", settings.rag_model_cache_dir)
            started = time.perf_counter()
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer(settings.rag_local_embedding_model, device=settings.rag_local_embedding_device, cache_folder=settings.rag_model_cache_dir or None)
            _load_seconds = round(time.perf_counter() - started, 2)
            logger.info("Local embedding model loaded in %.2fs: %s", _load_seconds, settings.rag_local_embedding_model)
        except Exception as error:
            _local_failed = True
            logger.warning("Local embedding model unavailable; lexical-only search: %s", type(error).__name__)
        return _local_model


def dimension() -> int | None:
    """Embedding dimension of the active provider, or None when embeddings are off."""
    provider = settings.rag_embedding_provider
    if provider == "local":
        model = _get_local_model()
        if model is None:
            return None
        getter = getattr(model, "get_embedding_dimension", None) or model.get_sentence_embedding_dimension
        return getter()
    if provider == "openai" and settings.openai_api_key:
        return settings.embedding_dimensions
    return None


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Embeddings for texts, or None when the provider is off or fails."""
    provider = settings.rag_embedding_provider
    if provider == "local":
        model = _get_local_model()
        if model is None:
            return None
        try:
            return [vector.tolist() for vector in model.encode(texts, normalize_embeddings=True, show_progress_bar=False)]
        except Exception as error:
            logger.warning("Local embedding failed; lexical-only search: %s", type(error).__name__)
            return None
    if provider == "openai":
        if not settings.openai_api_key:
            return None
        try:
            from .embeddings import create_embeddings
            return create_embeddings(texts)
        except Exception as error:
            logger.warning("OpenAI embedding failed; lexical-only search: %s", type(error).__name__)
            return None
    return None


def embed_text(text: str) -> list[float] | None:
    vectors = embed_texts([text])
    return vectors[0] if vectors else None


def verify_dimension() -> None:
    """Fail loudly (before indexing) when the model and pgvector dims disagree."""
    model_dimension = dimension()
    if model_dimension is not None and model_dimension != settings.embedding_dimensions:
        raise RuntimeError(f"Embedding dimension mismatch: configured pgvector dimension is {settings.embedding_dimensions} but the {settings.rag_embedding_provider} model produces {model_dimension}. Update EMBEDDING_DIMENSIONS (and migrate the vector columns) or choose a matching model.")


def warmup() -> bool:
    """Best-effort preload; a failure must never take the server down."""
    try:
        verify_dimension()
        return embed_text("워밍업 warmup") is not None
    except Exception as error:
        logger.warning("Embedding warmup failed; lexical-only search: %s", error)
        return False


def load_seconds() -> float | None:
    return _load_seconds


def reset_for_tests() -> None:
    global _local_model, _local_failed, _load_seconds
    with _lock:
        _local_model = None
        _local_failed = False
        _load_seconds = None
