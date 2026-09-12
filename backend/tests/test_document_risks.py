"""Deterministic tests for the employment-document review pipeline.

No OpenAI calls: classification, key-term extraction, and risk screening are
rule-based, and citations come from the reviewed lexical RAG corpus.
"""
import unittest

from app.config import settings
from app.document_explanation import analyze_document_risks, classify_document_type, explain_document, extract_key_terms

NORMAL_CONTRACT = (
    "표준근로계약서\n"
    "근로계약기간: 2026년 1월 1일부터 2026년 12월 31일까지\n"
    "근무장소: 전주시 소재 사업장\n"
    "근로시간: 09:00부터 18:00까지, 휴게시간 12:00~13:00\n"
    "임금: 월급 2,300,000원, 임금 지급일 매월 10일\n"
    "휴일: 주휴일 일요일, 연차 유급휴가는 근로기준에 따라 부여한다.\n"
    "연장근로 시 가산수당을 지급한다.\n"
)

RISKY_CONTRACT = (
    "근로계약서\n"
    "근로시간: 09:00부터 20:00까지\n"
    "임금: 시급 7,000원으로 하며 회사는 경영 사정에 따라 임금을 일방적으로 조정하거나 삭감할 수 있다.\n"
    "연장근로 수당은 기본 시급과 동일하게 지급한다.\n"
    "계약 위반 시 근로자는 위약금 500만원을 배상한다.\n"
)

UNRELATED_TEXT = "오늘은 하늘이 맑고 공원에서 산책하기 좋은 날씨입니다. 저녁에는 비빔밥을 먹었습니다."


class ClassificationTests(unittest.TestCase):
    def test_contract_payslip_and_notice_are_classified(self) -> None:
        self.assertEqual(classify_document_type(NORMAL_CONTRACT), "employment_contract")
        self.assertEqual(classify_document_type("3월 급여명세서: 기본급과 공제내역 안내"), "payslip")
        self.assertEqual(classify_document_type("체류기간 연장 관련 출입국 안내문입니다."), "administrative_notice")
        self.assertEqual(classify_document_type(UNRELATED_TEXT), "unknown")

    def test_key_terms_are_extracted_from_contract(self) -> None:
        terms = extract_key_terms(NORMAL_CONTRACT)
        for term in ("wage", "working_hours", "break_time", "contract_period", "holiday", "pay_day"):
            self.assertIn(term, terms)
        self.assertIn("월급", terms["wage"])


class RiskAnalysisTests(unittest.TestCase):
    def test_normal_contract_has_no_warnings(self) -> None:
        items = analyze_document_risks(NORMAL_CONTRACT, "employment_contract")
        self.assertNotIn("WARNING", {item.level for item in items})
        self.assertIn("SAFE", {item.level for item in items})

    def test_risky_contract_flags_penalty_wage_cut_and_overtime(self) -> None:
        items = analyze_document_risks(RISKY_CONTRACT, "employment_contract")
        levels = [item.level for item in items]
        self.assertIn("WARNING", levels)
        self.assertIn("CHECK", levels)
        clauses = " ".join(item.clause for item in items)
        self.assertIn("위약금", clauses)
        self.assertIn("동일하게", clauses)

    def test_missing_required_items_are_reported(self) -> None:
        items = analyze_document_risks(RISKY_CONTRACT, "employment_contract")
        missing = next(item for item in items if item.clause.startswith("기재 누락 가능"))
        self.assertIn("휴게시간", missing.clause)
        self.assertIn("휴일", missing.clause)

    def test_risk_items_include_server_built_official_sources(self) -> None:
        items = analyze_document_risks(RISKY_CONTRACT, "employment_contract")
        warning = next(item for item in items if item.level == "WARNING")
        self.assertTrue(warning.sources)
        for source in warning.sources:
            self.assertTrue(source.url.startswith("https://"))
            self.assertTrue(source.publisher)

    def test_no_definitive_illegality_language(self) -> None:
        items = analyze_document_risks(RISKY_CONTRACT, "employment_contract")
        for item in items:
            combined = item.reason + item.recommendation + " ".join(item.checks)
            self.assertNotIn("불법입니다", combined)
            self.assertNotIn("위반했습니다", combined)

    def test_unrelated_document_produces_no_risks(self) -> None:
        self.assertEqual(analyze_document_risks(UNRELATED_TEXT, "unknown"), [])


class ExplainDocumentPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        settings.openai_api_key = None

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key

    def test_text_document_works_without_api_key(self) -> None:
        result = explain_document(RISKY_CONTRACT.encode(), "text/plain", "contract.txt", "ko", False)
        self.assertEqual(result.document_type, "employment_contract")
        self.assertTrue(result.key_terms)
        self.assertTrue(result.risk_items)
        self.assertTrue(result.summary)
        self.assertTrue(any(guide.id == "missing-contract" for guide in result.related_guides))

    def test_unrelated_document_returns_no_risks_or_guides(self) -> None:
        result = explain_document(UNRELATED_TEXT.encode(), "text/plain", "note.txt", "ko", False)
        self.assertEqual(result.document_type, "unknown")
        self.assertEqual(result.risk_items, [])
        self.assertEqual(result.related_guides, [])

    def test_pdf_extraction_failure_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            explain_document(b"not-a-real-pdf", "application/pdf", "broken.pdf", "ko", False)

    def test_image_without_key_still_requires_key(self) -> None:
        with self.assertRaises(RuntimeError):
            explain_document(b"fake-image-bytes", "image/png", "scan.png", "ko", True)


if __name__ == "__main__":
    unittest.main()
