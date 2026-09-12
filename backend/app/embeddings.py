import hashlib
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from .config import settings
from .data import GUIDES
from .database import database_available, embedding_hashes, save_guide_embedding, search_guide_vectors
from .operations import acquire_ai_budget, record_ai_fallback
from .schemas import Guide

logger = logging.getLogger(__name__)


def guide_embedding_text(guide: Guide) -> str:
    parts: list[str] = []
    for language in ("ko", "en", "vi"):
        parts.extend([guide.title[language], guide.summary[language]])
        parts.extend(guide.steps[language])
        parts.extend(guide.required_documents[language])
        parts.extend(guide.cautions[language])
    return "\n".join(parts)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def create_embeddings(texts: list[str], client_factory: Callable[..., Any] | None = None) -> list[list[float]]:
    if client_factory is None:
        from openai import OpenAI
        client_factory = OpenAI
    client = client_factory(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
    response = client.embeddings.create(model=settings.embedding_model, input=texts, dimensions=settings.embedding_dimensions, encoding_format="float")
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def index_guides(client_factory: Callable[..., Any] | None = None) -> tuple[int, int]:
    if not settings.openai_api_key or not database_available():
        return 0, len(GUIDES)
    hashes = embedding_hashes()
    if hashes is None:
        return 0, len(GUIDES)
    pending = [(guide, guide_embedding_text(guide)) for guide in GUIDES if hashes.get(guide.id) != content_hash(guide_embedding_text(guide))]
    if not pending:
        return 0, 0
    if not acquire_ai_budget():
        return 0, len(pending)
    try:
        vectors = create_embeddings([text for _, text in pending], client_factory)
        saved = sum(save_guide_embedding(guide.id, vector, settings.embedding_model, content_hash(text)) for (guide, text), vector in zip(pending, vectors))
        return saved, len(pending) - saved
    except Exception as error:
        record_ai_fallback()
        logger.warning("Guide embedding indexing failed: %s", type(error).__name__)
        return 0, len(pending)


def search_guides_semantically(question: str, client_factory: Callable[..., Any] | None = None, searcher: Callable[[list[float], int, float], list[tuple[Guide, float]] | None] | None = None) -> list[Guide]:
    if not settings.openai_api_key or (searcher is None and not database_available()) or not acquire_ai_budget():
        return []
    try:
        safe_question = re.sub(r"(?<!\d)\d{6}[- ]?\d{6,7}(?!\d)", "[REDACTED]", question)
        vector = create_embeddings([safe_question], client_factory)[0]
        matches = (searcher or search_guide_vectors)(vector, 3, settings.vector_similarity_threshold)
        if not matches:
            return []
        guides = [guide for guide, _ in matches]
        return sorted(guides, key=lambda guide: guide.id != "industrial-accident")
    except Exception as error:
        record_ai_fallback()
        logger.warning("Vector guide search failed: %s", type(error).__name__)
        return []
