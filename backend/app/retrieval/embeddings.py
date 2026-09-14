# 가이드 임베딩 색인과 가이드 시맨틱 검색을 담당하는 파일
import hashlib
import json
import logging
import re
from collections.abc import Callable
from typing import Any

from ..core.config import settings
from ..data.seed import GUIDES
from ..infra.database import database_available, embedding_hashes, save_guide_embedding, search_guide_vectors
from ..infra.operations import acquire_ai_budget, record_ai_fallback
from ..core.schemas import Guide

logger = logging.getLogger(__name__)


def guide_embedding_text(guide: Guide) -> str:
    """Korean title+summary (+ English title as an anchor).

    The multilingual model aligns languages in one vector space, so a compact
    single-language passage matches ko/en/vi queries better than concatenating
    all translations (which dilutes the vector and overflows the model's
    sequence window)."""
    return "\n".join([guide.title["ko"], guide.title["en"], guide.summary["ko"]])


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def create_embeddings(texts: list[str], client_factory: Callable[..., Any] | None = None) -> list[list[float]]:
    if client_factory is None:
        from openai import OpenAI
        client_factory = OpenAI
    client = client_factory(api_key=settings.openai_api_key, timeout=settings.openai_timeout_seconds)
    response = client.embeddings.create(model=settings.embedding_model, input=texts, dimensions=settings.embedding_dimensions, encoding_format="float")
    return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]


def index_guides(client_factory: Callable[..., Any] | None = None, force: bool = False) -> tuple[int, int]:
    """Embed guides through the shared EmbeddingService (same provider as RAG).

    An explicit client_factory keeps the legacy injected-OpenAI path for tests.
    force=True re-embeds every guide regardless of content hash (--reembed)."""
    from . import embedding_service
    if not database_available() or (client_factory is None and embedding_service.signature() == "none"):
        return 0, len(GUIDES)
    hashes = embedding_hashes()
    if hashes is None:
        return 0, len(GUIDES)
    pending = [(guide, guide_embedding_text(guide)) for guide in GUIDES if force or hashes.get(guide.id) != content_hash(guide_embedding_text(guide))]
    if not pending:
        return 0, 0
    try:
        if client_factory is not None:
            if not acquire_ai_budget():
                return 0, len(pending)
            vectors = create_embeddings([text for _, text in pending], client_factory)
            model = settings.embedding_model
        else:
            vectors = embedding_service.embed_texts([text for _, text in pending])
            model = embedding_service.signature()
            if vectors is None:
                return 0, len(pending)
        saved = sum(save_guide_embedding(guide.id, vector, model, content_hash(text)) for (guide, text), vector in zip(pending, vectors))
        return saved, len(pending) - saved
    except Exception as error:
        record_ai_fallback()
        logger.warning("Guide embedding indexing failed: %s", type(error).__name__)
        return 0, len(pending)


def search_guides_semantically(question: str, client_factory: Callable[..., Any] | None = None, searcher: Callable[[list[float], int, float], list[tuple[Guide, float]] | None] | None = None) -> list[Guide]:
    """Semantic guide fallback via the shared EmbeddingService.

    The stored-vector filter uses the provider signature, so stale vectors from
    another provider/model are never silently mixed into results."""
    from . import embedding_service
    if searcher is None and not database_available():
        return []
    try:
        safe_question = re.sub(r"(?<!\d)\d{6}[- ]?\d{6,7}(?!\d)", "[REDACTED]", question)
        if client_factory is not None:
            if not settings.openai_api_key or not acquire_ai_budget():
                return []
            vector = create_embeddings([safe_question], client_factory)[0]
            model = settings.embedding_model
        else:
            if embedding_service.signature() == "none":
                return []
            vector = embedding_service.embed_text(safe_question)
            model = embedding_service.signature()
            if vector is None:
                return []
        matches = (searcher or (lambda v, limit, threshold: search_guide_vectors(v, limit, threshold, model=model)))(vector, 3, settings.vector_similarity_threshold)
        if not matches:
            return []
        guides = [guide for guide, _ in matches]
        return sorted(guides, key=lambda guide: guide.id != "industrial-accident")
    except Exception as error:
        record_ai_fallback()
        logger.warning("Vector guide search failed: %s", type(error).__name__)
        return []
