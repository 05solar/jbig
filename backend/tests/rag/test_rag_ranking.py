# 하이브리드 점수 병합·랭킹·증거 선택·게이트·쿼리 재작성을 검증하는 테스트 파일
"""Unit tests for hybrid score merging, ranking, evidence selection, and gates.

No OpenAI API is used: embeddings and LLM clients are deterministic fakes.
"""
import unittest
from unittest.mock import patch

from fakes import FailingLLMClient, FakeLLMClient, FakeLLMResponses, fake_create_embeddings

from app.chat.ai_consultation import generate_rag_answer, rewrite_search_query
from app.core.config import settings
from app.retrieval.rag import OfficialChunk, _ranking_score, freshness_for_document, merge_scores, register_document, search_index, select_evidence
from app.core.schemas import ConsultationResponse, RAGDocument


def empty_result(language: str = "ko") -> ConsultationResponse:
    return ConsultationResponse(language=language, message="", guide=None, guides=[], agencies=[])


def make_document(document_id: str = "doc", **overrides) -> RAGDocument:
    fields = dict(document_id=document_id, title="공식 안내", publisher="고용노동부", category="labor", original_text="본문", source_url="https://www.moel.go.kr/", language="ko", collected_at="2026-09-12", verified_at="2026-09-12", version="1", content_hash="hash", status="active")
    fields.update(overrides)
    return RAGDocument(**fields)


class MergeAndRankingTests(unittest.TestCase):
    def test_weighted_merge_of_both_signals(self):
        self.assertAlmostEqual(merge_scores(0.5, 0.9), 0.7)

    def test_single_signal_is_not_penalized(self):
        self.assertEqual(merge_scores(0.6, None), 0.6)
        self.assertEqual(merge_scores(None, 0.8), 0.8)

    def test_weights_are_configurable(self):
        original = settings.rag_weight_lexical, settings.rag_weight_vector
        settings.rag_weight_lexical, settings.rag_weight_vector = 3.0, 1.0
        try:
            self.assertAlmostEqual(merge_scores(0.4, 0.8), 0.5)
        finally:
            settings.rag_weight_lexical, settings.rag_weight_vector = original

    def test_official_source_outranks_low_authority_at_equal_relevance(self):
        official = OfficialChunk(make_document("official", document_type="law"), "official:0", "본문", 0)
        weak = OfficialChunk(make_document("weak", publisher="알 수 없는 기관", source_url="https://www.moel.go.kr/", document_type="live"), "weak:0", "본문", 0)
        self.assertGreater(_ranking_score(official, 0.5), _ranking_score(weak, 0.5))

    def test_freshness_scores(self):
        self.assertEqual(freshness_for_document(make_document()), 1.0)
        self.assertLess(freshness_for_document(make_document(status="fetch_failed")), 1.0)
        self.assertLess(freshness_for_document(make_document(next_check_at="2020-01-01T00:00:00+00:00")), 1.0)
        self.assertLess(freshness_for_document(make_document(document_type="live")), 1.0)

    def test_vector_and_lexical_scores_merge_in_search_index(self):
        document, chunks = register_document(document_id="hybrid", title="하이브리드 검증 문서", publisher="고용노동부", category="labor", text="임금 관련 공식 확인 내용입니다.", source_url="https://www.moel.go.kr/")
        chunk = chunks[0]
        original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"
        try:
            with patch("app.retrieval.rag.search_official_documents", return_value=[(chunk, 0.5)]), \
                 patch("app.retrieval.embeddings.create_embeddings", side_effect=fake_create_embeddings), \
                 patch("app.infra.database.search_rag_vectors", return_value=[(document, chunk.chunk_id, chunk.text, 0, 0.9)]):
                results = search_index("임금")
            self.assertEqual(len(results), 1)
            self.assertAlmostEqual(results[0][1], 0.7)
        finally:
            settings.openai_api_key = original_key


class EvidenceSelectionTests(unittest.TestCase):
    def make_chunks(self, document_id: str, texts: list[str]):
        document = make_document(document_id)
        return [(OfficialChunk(document, f"{document_id}:{index}", text, index), 0.9 - index * 0.01) for index, text in enumerate(texts)]

    def test_caps_chunks_per_document(self):
        matches = self.make_chunks("doc", ["임금 지급 기준 안내", "체불 진정 절차 안내", "수당 계산 방법 안내"])
        selected = select_evidence(matches)
        self.assertEqual(len(selected), settings.rag_max_chunks_per_document)

    def test_removes_near_duplicate_chunks_across_documents(self):
        first = self.make_chunks("one", ["임금 체불 진정은 노동관서에 접수합니다."])
        second = self.make_chunks("two", ["임금 체불 진정은 노동관서에 접수합니다!"])
        selected = select_evidence(first + second)
        self.assertEqual(len(selected), 1)

    def test_respects_total_budget_and_rank_order(self):
        matches = []
        for index in range(6):
            matches += self.make_chunks(f"doc{index}", [f"문서 {index}번의 서로 다른 공식 안내 내용 {index}"])
        selected = select_evidence(matches)
        self.assertEqual(len(selected), settings.rag_max_evidence)
        self.assertEqual([chunk.document.document_id for chunk, _ in selected], ["doc0", "doc1", "doc2", "doc3"])


class AnswerGateTests(unittest.TestCase):
    def setUp(self):
        self.original_key = settings.openai_api_key
        settings.openai_api_key = None

    def tearDown(self):
        settings.openai_api_key = self.original_key

    def test_low_relevance_triggers_insufficient_evidence(self):
        original = settings.rag_min_confident_relevance
        settings.rag_min_confident_relevance = 0.99
        try:
            matches = search_index("숙소비 공제")
            self.assertTrue(matches)
            result = generate_rag_answer(empty_result(), "숙소비 공제", matches)
            self.assertEqual(result.answer_mode, "insufficient_evidence")
            self.assertFalse(result.evidence_sufficient)
            self.assertTrue(result.sources)
            self.assertTrue(result.follow_up_questions)
        finally:
            settings.rag_min_confident_relevance = original

    def test_no_matches_returns_follow_up_questions(self):
        result = generate_rag_answer(empty_result("en"), "unknown topic", [])
        self.assertEqual(result.answer_mode, "insufficient_evidence")
        self.assertTrue(result.follow_up_questions)

    def test_evidence_selection_limits_llm_context_documents(self):
        original = settings.rag_max_evidence
        settings.rag_max_evidence = 2
        try:
            matches = search_index("숙소비를 월급에서 공제했어요")
            self.assertGreater(len(matches), 2)
            result = generate_rag_answer(empty_result(), "숙소비 공제", matches)
            self.assertEqual(len(result.sources), 2)
        finally:
            settings.rag_max_evidence = original


class QueryRewriteTests(unittest.TestCase):
    def setUp(self):
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_query_rewrite_enabled

    def tearDown(self):
        settings.openai_api_key = self.original_key
        settings.rag_query_rewrite_enabled = self.original_flag

    def test_disabled_by_default_returns_none(self):
        settings.openai_api_key = "test-key"
        settings.rag_query_rewrite_enabled = False
        self.assertIsNone(rewrite_search_query("월급 안 줘요", FakeLLMClient))

    @patch("app.chat.ai_consultation.acquire_ai_budget", return_value=True)
    def test_enabled_rewrite_uses_fake_client_and_redacts(self, _budget):
        settings.openai_api_key = "test-key"
        settings.rag_query_rewrite_enabled = True
        original_output = FakeLLMResponses.output_text
        FakeLLMResponses.output_text = "임금체불 진정"
        try:
            rewritten = rewrite_search_query("900101-1234567 월급 문제", FakeLLMClient)
            self.assertEqual(rewritten, "임금체불 진정")
            params = FakeLLMClient.last_params
            self.assertFalse(params["store"])
            self.assertNotIn("900101-1234567", params["input"])
        finally:
            FakeLLMResponses.output_text = original_output

    @patch("app.chat.ai_consultation.acquire_ai_budget", return_value=True)
    def test_rewrite_failure_returns_none(self, _budget):
        settings.openai_api_key = "test-key"
        settings.rag_query_rewrite_enabled = True
        self.assertIsNone(rewrite_search_query("질문", FailingLLMClient))


if __name__ == "__main__":
    unittest.main()
