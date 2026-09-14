# 가이드 임베딩의 공용 서비스 사용과 캐시 index_version 무효화를 검증하는 테스트 파일
"""Guide-embedding unification and cache index-versioning tests. No OpenAI calls."""
import unittest
from unittest.mock import MagicMock, patch

import app.retrieval.rag as rag
from app.core.config import settings
from app.data.seed import GUIDES
from app.retrieval.embeddings import index_guides, search_guides_semantically
from app.retrieval.rag import SAMPLE_DOCUMENTS, search_rag_db

from rag.test_db_search import LOCAL_READY, make_fake_fetch

DB_ROWS = [(document, chunk.chunk_id, chunk.text, chunk.chunk_index) for document, chunks in SAMPLE_DOCUMENTS for chunk in chunks]

FAKE_DIM_VECTOR = [0.1] * 384


class GuideEmbeddingServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_provider = settings.rag_embedding_provider
        settings.rag_embedding_provider = "local"

    def tearDown(self) -> None:
        settings.rag_embedding_provider = self.original_provider

    @patch("app.retrieval.embeddings.database_available", return_value=True)
    @patch("app.retrieval.embeddings.embedding_hashes", return_value={})
    def test_guide_indexing_uses_shared_service_and_signature(self, _hashes, _available) -> None:
        saved: list = []
        openai_spy = MagicMock(side_effect=AssertionError("OpenAI embedding path must not be used"))
        with patch("app.retrieval.embeddings.save_guide_embedding", side_effect=lambda gid, vec, model, chash: saved.append((gid, len(vec), model)) or True), \
             patch("app.retrieval.embedding_service.embed_texts", return_value=[FAKE_DIM_VECTOR] * len(GUIDES)), \
             patch("app.retrieval.embeddings.create_embeddings", openai_spy):
            indexed, failed = index_guides()
        self.assertEqual(indexed, len(GUIDES))
        self.assertEqual(failed, 0)
        openai_spy.assert_not_called()
        from app.retrieval import embedding_service
        for _gid, dim, model in saved:
            self.assertEqual(dim, 384)
            self.assertEqual(model, embedding_service.signature())

    @patch("app.retrieval.embeddings.database_available", return_value=True)
    def test_guide_search_uses_service_and_passes_signature_filter(self, _available) -> None:
        captured: dict = {}

        def searcher(vector, limit, threshold):
            captured.update(vector=vector, limit=limit, threshold=threshold)
            return [(next(g for g in GUIDES if g.id == "unpaid-wages"), 0.9)]

        openai_spy = MagicMock(side_effect=AssertionError("OpenAI embedding path must not be used"))
        with patch("app.retrieval.embedding_service.embed_text", return_value=FAKE_DIM_VECTOR), \
             patch("app.retrieval.embeddings.create_embeddings", openai_spy):
            result = search_guides_semantically("사장님이 돈을 계속 미뤄요", searcher=searcher)
        self.assertEqual(result[0].id, "unpaid-wages")
        self.assertEqual(len(captured["vector"]), 384)
        openai_spy.assert_not_called()

    def test_none_provider_disables_guide_vector_search_safely(self) -> None:
        settings.rag_embedding_provider = "none"
        searcher = MagicMock()
        self.assertEqual(search_guides_semantically("아무 질문", searcher=searcher), [])
        searcher.assert_not_called()
        with patch("app.retrieval.embeddings.database_available", return_value=True), patch("app.retrieval.embeddings.embedding_hashes", return_value={}):
            indexed, skipped = index_guides()
        self.assertEqual(indexed, 0)

    @patch("app.retrieval.embeddings.database_available", return_value=True)
    def test_embedding_failure_falls_back_to_empty_result(self, _available) -> None:
        with patch("app.retrieval.embedding_service.embed_text", return_value=None):
            self.assertEqual(search_guides_semantically("임금 문제", searcher=MagicMock()), [])

    @unittest.skipUnless(LOCAL_READY, "local sentence-transformers model is not available")
    def test_local_guide_vectors_are_384_dimensional(self) -> None:
        from app.retrieval import embedding_service
        from app.retrieval.embeddings import guide_embedding_text
        vector = embedding_service.embed_text(guide_embedding_text(GUIDES[0]))
        self.assertEqual(len(vector), 384)


class CacheIndexVersionTests(unittest.TestCase):
    def setUp(self) -> None:
        rag._search_cache.clear()
        self.original_provider = settings.rag_embedding_provider
        settings.rag_embedding_provider = "none"

    def tearDown(self) -> None:
        settings.rag_embedding_provider = self.original_provider
        rag._search_cache.clear()

    def test_index_version_change_invalidates_search_cache(self) -> None:
        fetch = MagicMock(side_effect=make_fake_fetch(DB_ROWS))
        with patch("app.infra.database.fetch_lexical_candidates", fetch), \
             patch("app.infra.database.rag_index_version", side_effect=["1", "1", "2"]):
            first = search_rag_db("숙소비 공제", category="labor")
            second = search_rag_db("숙소비 공제", category="labor")  # cache hit on version 1
            self.assertEqual(fetch.call_count, 1)
            third = search_rag_db("숙소비 공제", category="labor")  # version 2 -> miss
            self.assertEqual(fetch.call_count, 2)
        self.assertEqual([c.chunk_id for c, _ in first], [c.chunk_id for c, _ in second])
        self.assertEqual([c.chunk_id for c, _ in first], [c.chunk_id for c, _ in third])
        versions = {key[4] for key in rag._search_cache}
        self.assertIn("2", versions)

    def test_cache_key_contains_provider_and_version(self) -> None:
        with patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS)), \
             patch("app.infra.database.rag_index_version", return_value="7"):
            search_rag_db("숙소비 공제", category="labor")
        key = next(iter(rag._search_cache))
        self.assertEqual(key[3], "none")
        self.assertEqual(key[4], "7")


class GuideSemanticFixtureTests(unittest.TestCase):
    """ko/en/vi guide classification through the injected searcher (no DB, no API)."""

    def setUp(self) -> None:
        self.original_provider = settings.rag_embedding_provider
        settings.rag_embedding_provider = "local"

    def tearDown(self) -> None:
        settings.rag_embedding_provider = self.original_provider

    def fake_searcher_for(self, guide_id):
        guide = next(g for g in GUIDES if g.id == guide_id)
        return lambda vector, limit, threshold: [(guide, 0.8)]

    def run_query(self, question, guide_id):
        with patch("app.retrieval.embedding_service.embed_text", return_value=FAKE_DIM_VECTOR):
            result = search_guides_semantically(question, searcher=self.fake_searcher_for(guide_id))
        self.assertEqual(result[0].id, guide_id, question)

    def test_korean_english_vietnamese_guide_queries(self) -> None:
        self.run_query("월급 못 받았어요", "unpaid-wages")
        self.run_query("비자 연장하고 싶어요", "stay-extension")
        self.run_query("I was not paid this month", "unpaid-wages")
        self.run_query("Tôi muốn gia hạn visa", "stay-extension")


if __name__ == "__main__":
    unittest.main()
