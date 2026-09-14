# 챗봇·OCR 출력 언어 일관성(선택 언어 강제·원문 보존)을 검증하는 테스트 파일
"""Output-language consistency for chat and OCR. No OpenAI calls (mocks only).

The selected UI language (ko/en/vi) is the single source of truth for every
user-facing explanation. Korean is allowed only in verbatim quotes and source
metadata (title/publisher/URL), which must stay unmodified.
"""
import re
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.chat.ai_consultation import generate_rag_answer, validate_output_language
from app.core.config import settings
from app.documents.document_explanation import analyze_document_risks, explain_document
from app.main import app
from app.documents.ocr import OCRResult
from app.infra.operations import reset_for_tests
from app.retrieval.rag import search_index
from app.core.schemas import ConsultationResponse

client = TestClient(app)

HANGUL = re.compile(r"[가-힣]")

REPRO_QUESTION = (
    "I am an undocumented immigrant, and the boss is only paying me 70% of the legally minimum wage in Korea. "
    "I want to formally raise an issue about this, but the boss is threatening that if I file a complaint, "
    "they will reveal that I am an undocumented immigrant and deport me. What should I do about this?"
)

FORBIDDEN_KOREAN_FRAGMENTS = ("검색된 자료", "임금은", "근로자", "확인된 내용", "관련 내용")


def assert_no_unexpected_korean(test, text, context=""):
    test.assertIsNone(HANGUL.search(text), f"unexpected Korean in {context}: {text[:160]}")


def empty_result(language):
    return ConsultationResponse(language=language, message="", guide=None, guides=[], agencies=[])


class ChatOutputLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        settings.openai_api_key = None

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key

    def test_english_rag_answer_contains_no_korean_body(self) -> None:
        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("en"), "housing fee deduction", matches)
        self.assertEqual(result.answer_mode, "rag")
        assert_no_unexpected_korean(self, result.message, "en rag message")
        self.assertTrue(HANGUL.search(result.sources[0].title), "source title must keep the original language")

    def test_vietnamese_rag_answer_contains_no_korean_body(self) -> None:
        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("vi"), "trừ tiền nhà vào lương", matches)
        assert_no_unexpected_korean(self, result.message, "vi rag message")
        self.assertIn("Tài liệu", result.message)

    def test_korean_answer_still_quotes_evidence(self) -> None:
        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("ko"), "숙소비 공제", matches)
        self.assertIn("검색된 공식 자료에서 확인된 내용", result.message)

    def test_repro_sensitive_english_question_is_fully_english(self) -> None:
        # The long free-text question dilutes lexical overlap below the
        # threshold, so retrieve evidence with its core terms and run the
        # sensitive-topic path against the original question — this is the
        # exact code path that previously dumped Korean into English answers.
        matches = search_index("I was not paid the minimum wage")
        self.assertTrue(matches)
        result = generate_rag_answer(empty_result("en"), REPRO_QUESTION, matches)
        for fragment in FORBIDDEN_KOREAN_FRAGMENTS:
            self.assertNotIn(fragment, result.message, fragment)
        assert_no_unexpected_korean(self, result.message, "sensitive en message")
        self.assertIn("1350", result.message)
        self.assertTrue(result.sources)

    def test_llm_failure_fallback_is_localized(self) -> None:
        settings.openai_api_key = "test-key"

        class FailingClient:
            def __init__(self, **kwargs) -> None:
                raise RuntimeError("outage")

        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("en"), "housing deduction", matches, FailingClient)
        self.assertEqual(result.answer_mode, "rag")
        assert_no_unexpected_korean(self, result.message, "en llm-failure fallback")

    def test_language_violation_triggers_one_retry_then_fallback(self) -> None:
        settings.openai_api_key = "test-key"
        calls = {"count": 0}

        class KoreanResponses:
            def create(self, **kwargs):
                calls["count"] += 1
                return type("Response", (), {"output_text": "이 답변은 전부 한국어로 작성되어 언어 지시를 위반했습니다."})()

        class KoreanClient:
            def __init__(self, **kwargs) -> None:
                self.responses = KoreanResponses()

        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("en"), "housing deduction", matches, KoreanClient)
        self.assertEqual(calls["count"], 2)  # initial + exactly one retry
        assert_no_unexpected_korean(self, result.message, "post-retry fallback")

    def test_authority_insufficient_is_vietnamese_for_vi(self) -> None:
        from app.retrieval.rag import OfficialChunk
        from app.core.schemas import RAGDocument
        document = RAGDocument(document_id="live", title="운영 정보", publisher="알 수 없는 기관", category="labor", original_text="대기시간 안내", source_url="https://www.moel.go.kr/", language="ko", collected_at="2026-09-13", verified_at="2026-09-13", version="1", content_hash="hash", document_type="live", status="active")
        result = generate_rag_answer(empty_result("vi"), "thời gian chờ", [(OfficialChunk(document, "live:0", document.original_text, 0), 0.9)])
        self.assertEqual(result.answer_mode, "insufficient_evidence")
        self.assertIn("Độ tin cậy", result.message)
        assert_no_unexpected_korean(self, result.message, "vi authority message")

    def test_validate_output_language_helper(self) -> None:
        self.assertTrue(validate_output_language("완전한 한국어 답변", "ko"))
        self.assertTrue(validate_output_language("A fully English answer.", "en"))
        self.assertFalse(validate_output_language("영어를 요청했지만 이 문장은 한국어입니다.", "en"))
        self.assertTrue(validate_output_language("English with one term (임금체불) kept.", "en"))


class EndToEndLanguageTests(unittest.TestCase):
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

    def test_vietnamese_out_of_scope_follow_up_is_vietnamese(self) -> None:
        response = client.post("/api/consultations", json={"question": "Thời tiết hôm nay thế nào?", "language": "vi"})
        body = response.json()
        self.assertEqual(body["answer_mode"], "insufficient_evidence")
        self.assertTrue(body["follow_up_questions"])
        self.assertIn("Vui lòng", body["follow_up_questions"][0])

    def test_english_sensitive_consultation_endpoint(self) -> None:
        response = client.post("/api/consultations", json={"question": REPRO_QUESTION, "language": "en"})
        body = response.json()
        for fragment in FORBIDDEN_KOREAN_FRAGMENTS:
            self.assertNotIn(fragment, body["message"], fragment)
        self.assertIsNone(HANGUL.search(body["message"]), body["message"][:160])


class OcrOutputLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.rag_use_sample_documents_for_tests = self.original_flag

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=OCRResult("", 0.0))
    def test_low_confidence_notice_is_vietnamese(self, _ocr) -> None:
        result = explain_document(b"png", "image/png", "scan.png", "vi", False)
        self.assertIn("Không thể đọc", result.summary)
        for action in result.actions:
            assert_no_unexpected_korean(self, action, "vi low-confidence action")

    def test_db_outage_notice_is_english(self) -> None:
        settings.rag_use_sample_documents_for_tests = False
        with patch("app.infra.database.database_available", return_value=False):
            items = analyze_document_risks("근로계약서 임금: 시급 9,500원 삭감할 수 있다", "employment_contract", "en")
        outage = next(item for item in items if "Reduction" in item.title or "Wage" in item.title)
        self.assertIn("temporarily unavailable", outage.problem)
        assert_no_unexpected_korean(self, outage.problem, "en outage problem")

    def test_ocr_llm_language_violation_falls_back_localized(self) -> None:
        settings.openai_api_key = "test-key"

        class KoreanSummaryResponses:
            def create(self, **kwargs):
                import json
                payload = {"summary": "이 요약은 한국어로 작성되어 언어 규칙을 위반했습니다.", "key_points": ["한국어 포인트"], "actions": [], "deadlines": [], "cautions": [], "related_guide_ids": []}
                return type("Response", (), {"output_text": json.dumps(payload)})()

        class KoreanSummaryClient:
            def __init__(self, **kwargs) -> None:
                self.responses = KoreanSummaryResponses()

        contract = "근로계약서 임금: 시급 9,500원, 근로시간 09:00부터 18:00까지 휴게 12:00~13:00 휴일 지급일"
        result = explain_document(contract.encode(), "text/plain", "contract.txt", "en", False, KoreanSummaryClient)
        self.assertIn("AI summarization is unavailable", result.summary)
        assert_no_unexpected_korean(self, result.summary, "en ocr fallback summary")


if __name__ == "__main__":
    unittest.main()
