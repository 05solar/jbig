# 위험 항목 설명의 다국어 일관성을 검증하는 테스트 파일
"""Language consistency tests for the rule-based document risk analysis.

No OpenAI calls: the analysis is deterministic and the RAG lookup is lexical.
Contract clauses are quoted verbatim (Korean); every explanation field must
follow the requested UI language.
"""
import re
import unittest

from app.documents.document_explanation import analyze_document_risks

from documents.test_document_risks import DETAILED_RISKY_CONTRACT

KOREAN = re.compile(r"[가-힣]")

EXPLANATION_FIELDS = ("title", "official_standard", "problem", "impact", "recommended_revision", "reason", "recommendation")


def explanation_text(item) -> str:
    return " ".join([*(getattr(item, field) for field in EXPLANATION_FIELDS), *item.checks])


class RiskLanguageTests(unittest.TestCase):
    def setUp(self) -> None:
        from app.core.config import settings
        self.settings = settings
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        self.settings.rag_use_sample_documents_for_tests = self.original_flag

    def test_english_explanations_contain_no_korean(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "en")
        self.assertTrue(items)
        for item in items:
            self.assertIsNone(KOREAN.search(explanation_text(item)), f"Korean found in {item.title}: {explanation_text(item)[:120]}")

    def test_vietnamese_explanations_contain_no_korean(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "vi")
        self.assertTrue(items)
        for item in items:
            self.assertIsNone(KOREAN.search(explanation_text(item)), f"Korean found in {item.title}")
        wage = next(item for item in items if "tối thiểu" in item.title.lower() or "10,320" in item.problem)
        self.assertIn("10,320", wage.problem)

    def test_korean_output_is_preserved(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "ko")
        wage = next(item for item in items if item.title == "최저임금 미달 시급")
        self.assertIn("9,500원", wage.problem)
        self.assertIn("공식 고시 기준과 일치하지 않습니다", wage.problem)

    def test_english_keeps_original_clause_but_translates_explanation(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "en")
        cut = next(item for item in items if item.title == "Unilateral Wage Reduction Clause")
        self.assertIsNotNone(KOREAN.search(cut.clause))
        self.assertIn("without the worker's consent", cut.problem)
        self.assertIn("written agreement", cut.recommended_revision)
        wage = next(item for item in items if item.title == "Hourly Wage Below Minimum Wage")
        self.assertIn("9,500", wage.problem)
        self.assertIn("10,320", wage.problem)
        self.assertEqual(wage.difference, "-820")
        hours = next(item for item in items if item.title == "Daily Working Hours Exceeded")
        self.assertEqual(hours.detected_value, "9h 30m")
        self.assertEqual(hours.official_value, "8 hours/day")

    def test_source_metadata_is_never_translated(self) -> None:
        for language in ("en", "vi"):
            items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", language)
            wage = next(item for item in items if item.detected_value == "9500")
            self.assertEqual(wage.sources[0].title, "2026년 적용 최저임금 고시")
            self.assertEqual(wage.sources[0].publisher, "최저임금위원회")
            self.assertTrue(wage.sources[0].url.startswith("https://www.minimumwage.go.kr"))

    def test_unknown_language_falls_back_to_korean(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "ko")
        self.assertTrue(any(item.title == "임금 일방 삭감 조항" for item in items))


if __name__ == "__main__":
    unittest.main()
