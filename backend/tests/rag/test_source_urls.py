# 출처 상세 URL 보존과 generic 홈페이지 판정을 검증하는 테스트 파일
"""Source-URL accuracy: detail URLs preserved end-to-end, generic homepages flagged.

The source link must lead to the actual document used in the answer. A bare
agency homepage is marked url_specific=false so the UI disables the link
instead of sending the user to the wrong page. No fallback to publisher
homepages, no LLM-generated URLs.
"""
import unittest

from app.core.config import settings
from app.documents.document_explanation import analyze_document_risks
from app.retrieval.rag import SAMPLE_DOCUMENTS, is_specific_source_url, register_document, search_index, source_from_chunk

from documents.test_document_risks import DETAILED_RISKY_CONTRACT

DETAIL_URL = "https://www.moel.go.kr/policy/board/view.do?id=123&page=4"


class SpecificUrlDetectionTests(unittest.TestCase):
    def test_homepage_roots_are_generic(self) -> None:
        for url in ("https://www.moel.go.kr/", "https://www.moel.go.kr", "https://www.law.go.kr/", "https://www.hikorea.go.kr/"):
            self.assertFalse(is_specific_source_url(url), url)

    def test_paths_and_queries_are_specific(self) -> None:
        for url in (DETAIL_URL, "https://1350.moel.go.kr/rtmview.do?id=1000302992", "https://www.law.go.kr/법령/근로기준법/제56조", "https://www.minimumwage.go.kr/minWage/policy/decisionMain.do"):
            self.assertTrue(is_specific_source_url(url), url)


class SourceUrlRoundTripTests(unittest.TestCase):
    def test_path_and_query_survive_registration_and_response(self) -> None:
        document, chunks = register_document(document_id="url-roundtrip", title="상세 URL 보존 검증", publisher="고용노동부", category="labor", text="상세 URL이 응답까지 보존되는지 확인하는 검토 문서입니다.", source_url=DETAIL_URL)
        self.assertEqual(document.source_url, DETAIL_URL)
        source = source_from_chunk(chunks[0], 0.9)
        self.assertEqual(source.url, DETAIL_URL)
        self.assertTrue(source.url_specific)

    def test_generic_url_is_flagged_but_never_replaced(self) -> None:
        document, chunks = register_document(document_id="url-generic", title="홈페이지 URL 검증", publisher="고용노동부", category="labor", text="홈페이지 URL이 플래그되는지 확인하는 검토 문서입니다.", source_url="https://www.moel.go.kr/")
        source = source_from_chunk(chunks[0], 0.9)
        self.assertEqual(source.url, "https://www.moel.go.kr/")  # preserved, not swapped
        self.assertFalse(source.url_specific)


class CorpusUrlAuditTests(unittest.TestCase):
    def test_law_and_minimum_wage_documents_have_detail_urls(self) -> None:
        by_id = {document.document_id: document for document, _ in SAMPLE_DOCUMENTS}
        self.assertIn("minWage/policy/decisionMain.do", by_id["minimumwage-2026-notice"].source_url)
        self.assertIn("법령/근로기준법/제56조", by_id["moel-overtime-premium-standard"].source_url)
        self.assertIn("법령/근로기준법/제60조", by_id["moel-annual-leave-standard"].source_url)
        self.assertIn("법령/근로기준법/제43조", by_id["moel-wage-cut-penalty-prohibition"].source_url)
        for document_id in ("minimumwage-2026-notice", "minimumwage-check-guide", "moel-overtime-premium-standard", "moel-working-hours-standard", "moel-weekly-holiday-standard", "moel-annual-leave-standard", "moel-wage-cut-penalty-prohibition", "moel-internal-rules-limit"):
            self.assertTrue(is_specific_source_url(by_id[document_id].source_url), document_id)

    def test_remaining_generic_documents_are_identified(self) -> None:
        generic = sorted(document.document_id for document, _ in SAMPLE_DOCUMENTS if not is_specific_source_url(document.source_url))
        self.assertEqual(len(generic), 13)
        self.assertIn("hikorea-stay-extension-status", generic)
        self.assertIn("moel-unpaid-wage-claim", generic)


class ResponseSourceUrlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.rag_use_sample_documents_for_tests = self.original_flag

    def test_chat_minimum_wage_source_links_detail_page(self) -> None:
        matches = search_index("최저임금보다 적게 받는 것 같아요")
        sources = [source_from_chunk(chunk, score) for chunk, score in matches]
        wage_source = next(source for source in sources if source.document_id.startswith("minimumwage"))
        self.assertIn("decisionMain.do", wage_source.url)
        self.assertTrue(wage_source.url_specific)

    def test_ocr_risk_sources_link_detail_pages(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        wage = next(item for item in items if item.detected_value == "9500")
        self.assertIn("decisionMain.do", wage.sources[0].url)
        self.assertTrue(wage.sources[0].url_specific)
        overtime = next(item for item in items if "가산수당" in item.title)
        self.assertIn("법령/근로기준법", overtime.sources[0].url)
        self.assertTrue(overtime.sources[0].url_specific)


if __name__ == "__main__":
    unittest.main()
