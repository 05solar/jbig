# LLM 상담 경로(마스킹·폴백·의미 분류)를 mock으로 검증하는 테스트 파일
import unittest

from app.chat.ai_consultation import generate_grounded_answer, redact_sensitive_data, select_guide_semantically
from app.core.config import settings
from app.chat.consultation import consult


class FakeResponses:
    def __init__(self) -> None:
        self.params = None

    def create(self, **kwargs):
        self.params = kwargs
        return type("Response", (), {"output_text": "Use the official guide and call 1350."})()


class FakeClient:
    last_instance = None

    def __init__(self, **kwargs) -> None:
        self.responses = FakeResponses()
        FakeClient.last_instance = self


class FailingClient:
    def __init__(self, **kwargs) -> None:
        raise RuntimeError("network unavailable")


class SemanticResponses:
    output = '{"matches":[{"guide_id":"unpaid-wages","confidence":0.93,"reason":"Payment was withheld"}]}'

    def create(self, **kwargs):
        self.params = kwargs
        return type("Response", (), {"output_text": self.output})()


class SemanticClient:
    last_instance = None

    def __init__(self, **kwargs) -> None:
        self.responses = SemanticResponses()
        SemanticClient.last_instance = self


class AiConsultationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key

    def test_redacts_identifier_before_sending(self) -> None:
        self.assertEqual(redact_sensitive_data("번호 900101-1234567"), "번호 [REDACTED]")

    def test_uses_responses_api_without_storage(self) -> None:
        result = generate_grounded_answer(consult("I was not paid", "en"), "ID 900101-1234567, I was not paid", FakeClient)
        self.assertEqual(result.answer_mode, "ai")
        self.assertIn("1350", result.message)
        params = FakeClient.last_instance.responses.params
        self.assertFalse(params["store"])
        self.assertNotIn("900101-1234567", params["input"])
        self.assertIn("GUIDE DATA", params["instructions"])

    def test_falls_back_when_api_fails(self) -> None:
        result = generate_grounded_answer(consult("I was fired", "en"), "I was fired", FailingClient)
        self.assertEqual(result.answer_mode, "rules")
        self.assertEqual(result.guide.id, "sudden-dismissal")

    def test_semantic_selection_finds_differently_worded_question(self) -> None:
        rules_result = consult("사장님이 약속한 돈을 계속 미루고 있어요", "ko")
        self.assertIsNone(rules_result.guide)
        result = select_guide_semantically(rules_result, "사장님이 약속한 돈을 계속 미루고 있어요", SemanticClient)
        self.assertEqual(result.guide.id, "unpaid-wages")
        params = SemanticClient.last_instance.responses.params
        self.assertEqual(params["text"]["format"]["type"], "json_schema")
        self.assertEqual(params["text"]["format"]["schema"]["properties"]["matches"]["maxItems"], 3)
        self.assertFalse(params["store"])

    def test_semantic_selection_requires_confidence_threshold(self) -> None:
        original = SemanticResponses.output
        SemanticResponses.output = '{"matches":[{"guide_id":"unpaid-wages","confidence":0.4,"reason":"uncertain"}]}'
        try:
            result = select_guide_semantically(consult("모호한 질문입니다", "ko"), "모호한 질문입니다", SemanticClient)
            self.assertIsNone(result.guide)
        finally:
            SemanticResponses.output = original


if __name__ == "__main__":
    unittest.main()
