# 문서 위험 분석(유형 분류·수치 비교·판정 강등·표현 원칙)을 검증하는 테스트 파일
"""Deterministic tests for the employment-document review pipeline.

No OpenAI calls: classification, key-term extraction, and risk screening are
rule-based, and citations come from the reviewed lexical RAG corpus.
"""
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.documents.document_explanation import analyze_document_risks, classify_document_type, explain_document, extract_key_terms

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

DETAILED_RISKY_CONTRACT = (
    "근로계약서\n"
    "근로시간: 09:00부터 19:00까지, 휴게시간 12:30~13:00\n"
    "임금: 시급 9,500원, 임금 지급일 매월 10일\n"
    "회사 사정이 어려운 경우 사업주는 사전 통지 없이 월 임금의 10% 범위에서 삭감할 수 있다.\n"
    "연장·야간·휴일근로 수당은 기본 시급과 동일하게 지급하며 별도 가산수당은 지급하지 않는다.\n"
    "입사 후 1년 전에는 연차가 없다.\n"
    "일요일은 무급 주휴일로 한다.\n"
    "회사 내부규정이 법령보다 우선한다.\n"
)


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
    def setUp(self) -> None:
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.rag_use_sample_documents_for_tests = self.original_flag

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

    def test_low_hourly_wage_is_compared_with_official_notice(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        wage = next(item for item in items if item.title == "최저임금 미달 시급")
        self.assertEqual(wage.level, "WARNING")
        self.assertEqual(wage.detected_value, "9500")
        self.assertEqual(wage.official_value, "10320")
        self.assertEqual(wage.difference, "-820")
        self.assertIn("9,500원", wage.problem)
        self.assertIn("10,320원", wage.problem)
        self.assertIn("820원", wage.problem)
        self.assertIn("10,320원 이상", wage.recommended_revision)
        self.assertIn("시간급 10,320원", wage.official_standard)
        self.assertTrue(wage.sources)

    def test_adequate_hourly_wage_is_marked_safe_with_comparison(self) -> None:
        items = analyze_document_risks("근로계약서 임금: 시급 11,000원 근로시간 휴일 휴게 지급일", "employment_contract")
        wage = next(item for item in items if item.title == "시급 기준 충족")
        self.assertEqual(wage.level, "SAFE")
        self.assertEqual(wage.official_value, "10320")
        self.assertEqual(wage.difference, "680")

    def test_overtime_conflict_includes_standard_and_condition(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        overtime = next(item for item in items if item.title == "가산수당 미지급 조항")
        self.assertEqual(overtime.level, "WARNING")
        self.assertIn("가산", overtime.official_standard)
        self.assertIn("5인", overtime.official_standard)
        self.assertIn("충돌", overtime.problem)
        self.assertIn("가산율을 적용", overtime.recommended_revision)

    def test_wage_cut_has_problem_impact_and_revision(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        cut = next(item for item in items if item.title == "임금 일방 삭감 조항")
        self.assertEqual(cut.level, "WARNING")
        self.assertIn("동의 없이", cut.problem)
        self.assertIn("낮아질 수 있습니다", cut.impact)
        self.assertIn("서면 합의", cut.recommended_revision)
        self.assertTrue(cut.sources)

    def test_daily_working_hours_are_calculated(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        hours = next(item for item in items if item.title == "1일 근로시간 초과")
        self.assertEqual(hours.detected_value, "9시간 30분")
        self.assertEqual(hours.official_value, "1일 8시간")
        self.assertEqual(hours.difference, "+1시간 30분")
        self.assertIn("9시간 30분", hours.problem)
        self.assertIn("1시간 30분", hours.problem)
        self.assertIn("8시간", hours.official_standard)

    def test_annual_leave_weekly_holiday_and_internal_rules_are_flagged(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        titles = {item.title for item in items}
        self.assertIn("연차 미부여 조항", titles)
        self.assertIn("무급 주휴일 조항", titles)
        self.assertIn("내부규정 우선 조항", titles)
        for title in ("연차 미부여 조항", "무급 주휴일 조항", "내부규정 우선 조항"):
            item = next(i for i in items if i.title == title)
            self.assertTrue(item.official_standard, title)
            self.assertTrue(item.sources, title)

    def test_all_warning_items_have_full_structured_fields(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        warnings = [item for item in items if item.level == "WARNING"]
        self.assertGreaterEqual(len(warnings), 3)
        for item in warnings:
            self.assertTrue(item.official_standard, item.title)
            self.assertTrue(item.problem, item.title)
            self.assertTrue(item.recommended_revision, item.title)
            self.assertTrue(item.sources, item.title)

    def test_ungrounded_rule_degrades_to_check_without_verdict(self) -> None:
        with patch("app.documents.document_explanation.search_official_documents", return_value=[]):
            items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        for item in items:
            self.assertNotEqual(item.level, "WARNING", item.title)
            self.assertNotIn("충돌합니다", item.problem, item.title)

    def test_no_absolute_illegality_claims_in_detailed_fields(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        for item in items:
            combined = " ".join([item.reason, item.recommendation, item.problem, item.impact, item.recommended_revision, item.official_standard, *item.checks])
            for forbidden in ("불법입니다", "위반했습니다", "100% 불법", "무조건", "반드시 처벌"):
                self.assertNotIn(forbidden, combined, item.title)


class ExplainDocumentPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.rag_use_sample_documents_for_tests = self.original_flag

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

    def test_scanned_pdf_without_consent_requires_consent(self) -> None:
        with self.assertRaises(PermissionError):
            explain_document(b"not-a-real-pdf", "application/pdf", "scan.pdf", "ko", False)

    def test_scanned_pdf_with_consent_but_no_key_raises_runtime_error(self) -> None:
        with self.assertRaises(RuntimeError):
            explain_document(b"not-a-real-pdf", "application/pdf", "scan.pdf", "ko", True)

    def test_oversized_file_reports_size_limit(self) -> None:
        with self.assertRaises(ValueError) as context:
            explain_document(b"x" * (settings.document_max_bytes + 1), "text/plain", "big.txt", "ko", False)
        self.assertIn("too large", str(context.exception))

    def test_image_without_key_still_requires_key(self) -> None:
        with self.assertRaises(RuntimeError):
            explain_document(b"fake-image-bytes", "image/png", "scan.png", "ko", True)

    def test_truncated_llm_json_falls_back_for_text_documents(self) -> None:
        class TruncatedResponses:
            def create(self, **kwargs):
                return type("Response", (), {"output_text": '{"summary": "잘린 응'})()

        class TruncatedClient:
            def __init__(self, **kwargs) -> None:
                self.responses = TruncatedResponses()

        settings.openai_api_key = "test-key"
        result = explain_document(RISKY_CONTRACT.encode(), "text/plain", "contract.txt", "ko", False, TruncatedClient)
        self.assertEqual(result.document_type, "employment_contract")
        self.assertTrue(result.risk_items)

        with self.assertRaises(RuntimeError):
            explain_document(b"fake-image-bytes", "image/png", "scan.png", "ko", True, TruncatedClient)


if __name__ == "__main__":
    unittest.main()
