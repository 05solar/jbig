# 로컬 임베딩 provider와 DB 후보 검색(전량 로드 금지·상한·캐시)을 검증하는 테스트 파일
"""Embedding service and candidate-set DB search tests. No OpenAI API calls."""
import unittest
from unittest.mock import MagicMock, patch

import app.retrieval.embedding_service as embedding_service
import app.retrieval.rag as rag
from app.core.config import settings
from app.retrieval.rag import SAMPLE_DOCUMENTS, search_index, search_official_documents, search_rag_db


def local_model_ready() -> bool:
    original = settings.rag_embedding_provider
    settings.rag_embedding_provider = "local"
    try:
        return embedding_service.embed_text("준비 확인") is not None
    finally:
        settings.rag_embedding_provider = original


LOCAL_READY = local_model_ready()

DB_ROWS = [(document, chunk.chunk_id, chunk.text, chunk.chunk_index) for document, chunks in SAMPLE_DOCUMENTS for chunk in chunks]


def make_fake_fetch(rows, captured=None):
    def fake_fetch(query_tokens, category, limit):
        if captured is not None:
            captured["lexical_limit"] = limit
        token_set = set(query_tokens)
        scored = []
        for document, chunk_id, text, index in rows:
            if category and document.category != category:
                continue
            overlap = len(rag._tokens(f"{document.title} {document.publisher} {text}") & token_set)
            if overlap:
                scored.append((overlap, (document, chunk_id, text, index)))
        scored.sort(key=lambda item: -item[0])
        return [row for _, row in scored[:limit]]

    return fake_fetch


class LocalEmbeddingProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_provider = settings.rag_embedding_provider
        settings.rag_embedding_provider = "local"

    def tearDown(self) -> None:
        settings.rag_embedding_provider = self.original_provider

    @unittest.skipUnless(LOCAL_READY, "local sentence-transformers model is not available")
    def test_local_provider_produces_stable_vectors(self) -> None:
        first = embedding_service.embed_text("임금을 받지 못했어요")
        second = embedding_service.embed_text("임금을 받지 못했어요")
        self.assertEqual(len(first), embedding_service.dimension())
        self.assertEqual(first, second)
        english = embedding_service.embed_text("I was not paid")
        self.assertEqual(len(english), len(first))

    @unittest.skipUnless(LOCAL_READY, "local sentence-transformers model is not available")
    def test_model_is_a_singleton(self) -> None:
        embedding_service.embed_text("한 번")
        first_model = embedding_service._local_model
        embedding_service.embed_text("두 번")
        self.assertIs(embedding_service._local_model, first_model)

    @unittest.skipUnless(LOCAL_READY, "local sentence-transformers model is not available")
    def test_dimension_mismatch_raises_readable_error(self) -> None:
        original = settings.embedding_dimensions
        settings.embedding_dimensions = 999
        try:
            with self.assertRaises(RuntimeError) as context:
                embedding_service.verify_dimension()
            self.assertIn("999", str(context.exception))
            self.assertIn(str(embedding_service.dimension()), str(context.exception))
        finally:
            settings.embedding_dimensions = original

    def test_none_provider_disables_embeddings_without_error(self) -> None:
        settings.rag_embedding_provider = "none"
        self.assertIsNone(embedding_service.embed_text("아무 텍스트"))
        self.assertIsNone(embedding_service.dimension())
        embedding_service.verify_dimension()  # must not raise
        self.assertEqual(embedding_service.signature(), "none")


class DbSearchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        rag._search_cache.clear()
        self.original_provider = settings.rag_embedding_provider
        settings.rag_embedding_provider = "none"

    def tearDown(self) -> None:
        settings.rag_embedding_provider = self.original_provider
        rag._search_cache.clear()

    def test_embedding_failure_falls_back_to_lexical_only(self) -> None:
        with patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS)), \
             patch("app.retrieval.embedding_service.embed_text", return_value=None):
            results = search_rag_db("숙소비를 월급에서 공제했어요", category="labor")
        self.assertTrue(results)
        self.assertEqual(results[0][0].document.document_id, "moel-wage-deduction-housing")

    def test_candidate_limits_are_respected(self) -> None:
        captured: dict = {}

        def fake_vectors(embedding, limit, threshold, model=None):
            captured["vector_limit"] = limit
            return []

        with patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS, captured)), \
             patch("app.retrieval.embedding_service.embed_text", return_value=[0.1] * settings.embedding_dimensions), \
             patch("app.infra.database.search_rag_vectors", side_effect=fake_vectors):
            search_rag_db("임금체불 문제", category="labor")
        self.assertEqual(captured["lexical_limit"], settings.rag_db_lexical_candidates)
        self.assertEqual(captured["vector_limit"], settings.rag_db_vector_candidates)

    def test_synthetic_corpus_never_loads_full_rows(self) -> None:
        base_doc = SAMPLE_DOCUMENTS[0][0]
        synthetic = [(base_doc.model_copy(update={"document_id": f"synthetic-{i}"}), f"synthetic-{i}:0", f"합성 청크 {i} 임금 관련 내용", 0) for i in range(5000)]
        with patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS + synthetic)) as fetch, \
             patch("app.infra.database.load_rag_chunks", side_effect=AssertionError("full corpus load during search")):
            results = search_rag_db("임금체불 진정 절차", category="labor")
        self.assertIsNotNone(results)
        self.assertLessEqual(len(results), settings.rag_top_k)
        self.assertEqual(fetch.call_count, 1)

    def test_hybrid_merge_uses_existing_weighted_policy(self) -> None:
        document, chunks = next(entry for entry in SAMPLE_DOCUMENTS if entry[0].document_id == "moel-unpaid-wage-claim")
        chunk = chunks[0]
        lexical_only = search_official_documents("임금체불 진정", category="labor", chunks=[chunk], limit=5)
        self.assertTrue(lexical_only)
        lexical_score = lexical_only[0][1]
        with patch("app.infra.database.fetch_lexical_candidates", return_value=[(document, chunk.chunk_id, chunk.text, chunk.chunk_index)]), \
             patch("app.retrieval.embedding_service.embed_text", return_value=[0.1] * settings.embedding_dimensions), \
             patch("app.infra.database.search_rag_vectors", return_value=[(document, chunk.chunk_id, chunk.text, chunk.chunk_index, 0.9)]):
            results = search_rag_db("임금체불 진정", category="labor")
        self.assertAlmostEqual(results[0][1], round((lexical_score + 0.9) / 2, 3))

    def test_ocr_and_chatbot_share_the_search_service(self) -> None:
        spy = MagicMock(return_value=[])
        with patch("app.retrieval.rag.search_rag_db", spy):
            search_index("임금 문제")
        self.assertTrue(spy.called)
        from app.documents.document_explanation import analyze_document_risks
        from documents.test_document_risks import DETAILED_RISKY_CONTRACT
        spy.reset_mock()
        with patch("app.retrieval.rag.search_rag_db", spy), patch("app.infra.database.database_available", return_value=True):
            analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        self.assertTrue(spy.called)

    def test_repeated_query_hits_cache(self) -> None:
        fetch = MagicMock(side_effect=make_fake_fetch(DB_ROWS))
        with patch("app.infra.database.fetch_lexical_candidates", fetch):
            first = search_rag_db("숙소비 공제", category="labor")
            second = search_rag_db("숙소비 공제", category="labor")
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual([c.chunk_id for c, _ in first], [c.chunk_id for c, _ in second])


if __name__ == "__main__":
    unittest.main()
