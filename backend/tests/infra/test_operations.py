# 레이트리밋·캐시·피드백 집계를 검증하는 테스트 파일
import unittest

from app.core.config import settings
from app.chat.consultation import consult
from app.infra.operations import allow_request, cache_key, get_cached, record_feedback, reset_for_tests, set_cached, status
from app.core.schemas import FeedbackRequest


class OperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()
        self.original_limit = settings.consultation_rate_limit

    def tearDown(self) -> None:
        settings.consultation_rate_limit = self.original_limit
        reset_for_tests()

    def test_rate_limit_uses_sliding_window(self) -> None:
        settings.consultation_rate_limit = 2
        self.assertTrue(allow_request("client", now=100))
        self.assertTrue(allow_request("client", now=101))
        self.assertFalse(allow_request("client", now=102))
        self.assertTrue(allow_request("client", now=161))

    def test_cache_does_not_store_question_text(self) -> None:
        key = cache_key("월급을 못 받았어요", "ko")
        self.assertNotIn("월급", key)
        result = consult("월급을 못 받았어요", "ko").model_copy(update={"consultation_id": "abc12345"})
        set_cached(key, result)
        cached = get_cached(key)
        self.assertTrue(cached.cached)
        self.assertEqual(cached.guide.id, "unpaid-wages")

    def test_feedback_is_aggregated_without_comment_text(self) -> None:
        feedback = FeedbackRequest(consultation_id="abc12345", rating="helpful")
        self.assertTrue(record_feedback(feedback))
        self.assertFalse(record_feedback(feedback))
        self.assertFalse(record_feedback(FeedbackRequest(consultation_id="abc12345", rating="not_helpful")))
        self.assertEqual(status().helpful, 1)


if __name__ == "__main__":
    unittest.main()
