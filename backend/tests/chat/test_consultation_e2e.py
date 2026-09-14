# 상담 API 전체 흐름(E2E 10개 시나리오)을 mock 기반으로 검증하는 테스트 파일
"""Mock-based end-to-end tests for POST /api/consultations.

The full pipeline (rate limit -> cache -> rules -> RAG search -> evidence ->
answer -> sources -> agencies) runs against the in-memory index with the
database disabled and every OpenAI surface replaced by deterministic fakes.
"""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from fakes import FailingLLMClient, FakeLLMClient

from app.core.config import settings
from app.main import app
from app.infra.operations import reset_for_tests
from app.retrieval.rag import OfficialChunk
from app.core.schemas import RAGDocument

client = TestClient(app)


def low_authority_match():
    document = RAGDocument(document_id="live-info", title="운영 정보", publisher="알 수 없는 기관", category="labor", original_text="접수 대기시간 안내입니다.", source_url="https://www.moel.go.kr/", language="ko", collected_at="2026-09-12", verified_at="2026-09-12", version="1", content_hash="hash", document_type="live", status="active")
    return [(OfficialChunk(document, "live-info:0", document.original_text, 0), 0.9)]


class ConsultationEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()
        self.original_key = settings.openai_api_key
        self.original_db = settings.database_enabled
        settings.openai_api_key = None
        settings.database_enabled = False

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.database_enabled = self.original_db
        reset_for_tests()

    def post(self, question: str, language: str = "ko", **extra):
        response = client.post("/api/consultations", json={"question": question, "language": language, **extra})
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_rag_answer_with_sources_and_agencies(self) -> None:
        body = self.post("숙소비를 월급에서 공제했어요")
        self.assertEqual(body["answer_mode"], "rag")
        self.assertTrue(body["evidence_sufficient"])
        self.assertTrue(body["sources"])
        self.assertEqual(body["sources"][0]["document_id"], "moel-wage-deduction-housing")
        self.assertTrue(all(source["url"].startswith("https://") for source in body["sources"]))
        self.assertIn("labor-office", {agency["id"] for agency in body["agencies"]})

    def test_out_of_scope_question_returns_insufficient_evidence(self) -> None:
        body = self.post("오늘 전주 날씨 알려줘")
        self.assertEqual(body["answer_mode"], "insufficient_evidence")
        self.assertFalse(body["evidence_sufficient"])
        self.assertEqual(body["sources"], [])
        self.assertTrue(body["follow_up_questions"])

    def test_low_authority_evidence_refuses_definitive_answer(self) -> None:
        with patch("app.main.search_index", return_value=low_authority_match()):
            body = self.post("접수 대기시간 알려주세요")
        self.assertEqual(body["answer_mode"], "insufficient_evidence")
        self.assertTrue(body["sources"])
        self.assertEqual(body["sources"][0]["trust_level"], "low")

    def test_guide_question_without_api_key_uses_rules(self) -> None:
        body = self.post("일하다 다쳤어요")
        self.assertEqual(body["answer_mode"], "rules")
        self.assertEqual(body["guide"]["id"], "industrial-accident")

    def test_openai_failure_falls_back_to_grounded_excerpt(self) -> None:
        settings.openai_api_key = "test-key"
        with patch("openai.OpenAI", FailingLLMClient):
            body = self.post("숙소비를 월급에서 공제했어요")
        self.assertEqual(body["answer_mode"], "rag")
        self.assertTrue(body["evidence_sufficient"])
        self.assertTrue(body["sources"])

    def test_daily_ai_budget_exhaustion_refuses_instead_of_guessing(self) -> None:
        settings.openai_api_key = "test-key"
        with patch("openai.OpenAI", FakeLLMClient), patch("app.chat.ai_consultation.acquire_ai_budget", return_value=False):
            body = self.post("숙소비를 월급에서 공제했어요")
        self.assertEqual(body["answer_mode"], "insufficient_evidence")
        self.assertTrue(body["sources"])

    def test_repeated_question_is_served_from_cache(self) -> None:
        first = self.post("숙소비를 월급에서 공제했어요")
        second = self.post("숙소비를 월급에서 공제했어요")
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["sources"], second["sources"])

    def test_rag_index_version_change_invalidates_cache(self) -> None:
        with patch("app.main.rag_index_version", side_effect=["1", "2"]):
            first = self.post("숙소비를 월급에서 공제했어요")
            second = self.post("숙소비를 월급에서 공제했어요")
        self.assertFalse(first["cached"])
        self.assertFalse(second["cached"])

    def test_vietnamese_question_gets_vietnamese_rag_answer(self) -> None:
        body = self.post("Tôi chưa được trả lương", language="vi")
        self.assertEqual(body["language"], "vi")
        self.assertEqual(body["answer_mode"], "rag")
        self.assertEqual(body["sources"][0]["document_id"], "moel-unpaid-dismissal-together")

    def test_out_of_scope_english_question_is_refused(self) -> None:
        body = self.post("Tell me the weather in Jeonju today", language="en")
        self.assertEqual(body["answer_mode"], "insufficient_evidence")
        self.assertTrue(body["follow_up_questions"])


if __name__ == "__main__":
    unittest.main()
