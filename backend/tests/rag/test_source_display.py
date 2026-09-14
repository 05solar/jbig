# 출처 표시용 번역 레이어(원본 보존+영/베 표시)를 검증하는 테스트 파일
"""Display-layer source translations: originals preserved, translated display added.

Deterministic dictionary only — no LLM/embedding calls anywhere.
"""
import re
import unittest

from app.chat.ai_consultation import generate_rag_answer
from app.core.config import settings
from app.documents.document_explanation import analyze_document_risks
from app.retrieval.rag import SAMPLE_DOCUMENTS, register_document, search_index, source_from_chunk
from app.core.schemas import ConsultationResponse
from app.retrieval.source_display import SOURCE_DISPLAY

from documents.test_document_risks import DETAILED_RISKY_CONTRACT

HANGUL = re.compile(r"[가-힣]")

PROHIBITION_CHUNK = next(chunks[0] for document, chunks in SAMPLE_DOCUMENTS if document.document_id == "moel-wage-cut-penalty-prohibition")


def empty_result(language):
    return ConsultationResponse(language=language, message="", guide=None, guides=[], agencies=[])


class DisplayFieldTests(unittest.TestCase):
    def test_english_display_added_and_original_preserved(self) -> None:
        source = source_from_chunk(PROHIBITION_CHUNK, 0.5, language="en")
        self.assertEqual(source.title, "임금 전액 지급과 위약금 예정 금지")
        self.assertEqual(source.publisher, "고용노동부")
        self.assertEqual(source.display_title, "Full Payment of Wages and Prohibition of Predetermined Penalties")
        self.assertEqual(source.display_publisher, "Ministry of Employment and Labor")
        self.assertIsNone(HANGUL.search(source.source_summary))
        self.assertIn("paid", source.source_summary)

    def test_vietnamese_display_added(self) -> None:
        source = source_from_chunk(PROHIBITION_CHUNK, 0.5, language="vi")
        self.assertEqual(source.title, "임금 전액 지급과 위약금 예정 금지")
        self.assertIn("tiền lương", source.display_title.lower())
        self.assertEqual(source.display_publisher, "Bộ Việc làm và Lao động")
        self.assertIsNone(HANGUL.search(source.source_summary))

    def test_korean_has_no_duplicate_display_fields(self) -> None:
        source = source_from_chunk(PROHIBITION_CHUNK, 0.5, language="ko")
        self.assertIsNone(source.display_title)
        self.assertIsNone(source.display_publisher)
        self.assertIsNone(source.source_summary)

    def test_url_and_flags_unchanged_by_translation(self) -> None:
        korean = source_from_chunk(PROHIBITION_CHUNK, 0.5, language="ko")
        english = source_from_chunk(PROHIBITION_CHUNK, 0.5, language="en")
        self.assertEqual(korean.url, english.url)
        self.assertEqual(korean.url_specific, english.url_specific)
        self.assertEqual(korean.authority_score, english.authority_score)
        self.assertEqual(korean.trust_level, english.trust_level)

    def test_unknown_document_falls_back_to_original_only(self) -> None:
        _document, chunks = register_document(document_id="display-unknown", title="사전에 없는 새 문서", publisher="고용노동부", category="labor", text="표시 사전에 등록되지 않은 새 검토 문서입니다.", source_url="https://www.moel.go.kr/a/b.do?id=1")
        source = source_from_chunk(chunks[0], 0.5, language="en")
        self.assertEqual(source.title, "사전에 없는 새 문서")
        self.assertIsNone(source.display_title)
        self.assertEqual(source.display_publisher, "Ministry of Employment and Labor")
        self.assertIsNone(source.source_summary)

    def test_all_corpus_documents_have_en_and_vi_entries(self) -> None:
        for document, _chunks in SAMPLE_DOCUMENTS:
            entry = SOURCE_DISPLAY.get(document.document_id)
            self.assertIsNotNone(entry, document.document_id)
            for language in ("en", "vi"):
                title, summary = entry[language]
                self.assertIsNone(HANGUL.search(title + summary), f"{document.document_id}:{language}")

    def test_summaries_do_not_invent_amounts(self) -> None:
        # Only the minimum-wage notice may contain a currency amount, mirroring its evidence.
        for document_id, languages in SOURCE_DISPLAY.items():
            for language in ("en", "vi"):
                _title, summary = languages[language]
                if document_id != "minimumwage-2026-notice":
                    self.assertNotRegex(summary, r"10[.,]320", f"{document_id}:{language}")


class ResponsePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.rag_use_sample_documents_for_tests = self.original_flag

    def test_chat_sources_carry_display_fields_for_english(self) -> None:
        matches = search_index("I was not paid the minimum wage")
        result = generate_rag_answer(empty_result("en"), "I was not paid the minimum wage", matches)
        self.assertTrue(result.sources)
        for source in result.sources:
            self.assertTrue(HANGUL.search(source.title), "original title preserved")
            self.assertTrue(source.display_title, source.document_id)
            self.assertTrue(source.source_summary, source.document_id)

    def test_chat_sources_have_no_display_fields_for_korean(self) -> None:
        matches = search_index("숙소비를 월급에서 공제했어요")
        result = generate_rag_answer(empty_result("ko"), "숙소비 공제", matches)
        self.assertTrue(all(source.display_title is None for source in result.sources))

    def test_ocr_sources_carry_display_fields_for_vietnamese(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract", "vi")
        wage = next(item for item in items if item.detected_value == "9500")
        source = wage.sources[0]
        self.assertEqual(source.title, "2026년 적용 최저임금 고시")
        self.assertIn("2026", source.display_title)
        self.assertIsNone(HANGUL.search(source.source_summary))

    def test_llm_failure_keeps_display_fields(self) -> None:
        settings.openai_api_key = "test-key"

        class FailingClient:
            def __init__(self, **kwargs) -> None:
                raise RuntimeError("outage")

        matches = search_index("I was not paid the minimum wage")
        result = generate_rag_answer(empty_result("en"), "unpaid minimum wage", matches, FailingClient)
        self.assertTrue(result.sources)
        self.assertTrue(result.sources[0].display_title)


if __name__ == "__main__":
    unittest.main()
