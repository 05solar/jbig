# 언어 감지와 키워드 가이드 매칭 규칙을 검증하는 테스트 파일
import unittest

from app.chat.consultation import consult, detect_language, find_guide, find_guides


class ConsultationTests(unittest.TestCase):
    def test_detects_supported_languages(self) -> None:
        self.assertEqual(detect_language("월급을 못 받았어요"), "ko")
        self.assertEqual(detect_language("I was not paid"), "en")
        self.assertEqual(detect_language("Tôi chưa được trả lương"), "vi")

    def test_matches_guides_in_three_languages(self) -> None:
        self.assertEqual(find_guide("회사에서 월급을 안 줍니다").id, "unpaid-wages")
        self.assertEqual(find_guide("I was fired without warning").id, "sudden-dismissal")
        self.assertEqual(find_guide("Tôi bị mất thẻ cư trú").id, "registration-card-reissue")

    def test_matches_indirect_dismissal_language(self) -> None:
        examples = [
            "회사에서 내일부터 나오지 말라고 했어요.",
            "사장님이 이제 그만 나오라고 합니다.",
            "My boss said don't come to work tomorrow.",
            "Chủ bảo tôi không cần đi làm từ ngày mai.",
        ]
        for question in examples:
            with self.subTest(question=question):
                self.assertEqual(find_guide(question).id, "sudden-dismissal")

    def test_returns_agencies_and_urgent_notice(self) -> None:
        result = consult("I was injured at work")
        self.assertEqual(result.guide.id, "industrial-accident")
        self.assertTrue(result.agencies)
        self.assertIn("119", result.urgent_notice)

    def test_unknown_question_has_safe_fallback(self) -> None:
        result = consult("Can you tell me something unrelated?")
        self.assertIsNone(result.guide)
        self.assertEqual(result.agencies, [])
        self.assertIn("1345", result.message)

    def test_compound_question_returns_multiple_guides(self) -> None:
        question = "월급을 못 받았고 회사에서 내일부터 나오지 말라고 했어요."
        guides = find_guides(question)
        self.assertEqual({guide.id for guide in guides}, {"unpaid-wages", "sudden-dismissal"})
        result = consult(question, "ko")
        self.assertEqual(len(result.guides), 2)
        self.assertEqual({agency.id for agency in result.agencies}, {"labor-office", "danuri"})

    def test_urgent_guide_is_prioritized(self) -> None:
        result = consult("월급도 못 받았고 일하다 다쳤어요", "ko")
        self.assertEqual(result.guides[0].id, "industrial-accident")
        self.assertIn("119", result.urgent_notice)


if __name__ == "__main__":
    unittest.main()
