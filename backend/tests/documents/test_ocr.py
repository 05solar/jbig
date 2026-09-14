# PaddleOCR 파이프라인(mock+실제 이미지 통합)을 검증하는 테스트 파일
"""OCR pipeline tests.

Deterministic tests mock the recognizer so they run everywhere with no engine
and no API key. Integration tests exercise the real PaddleOCR engine on
generated contract images and are skipped when the engine is not installed.
"""
import io
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.documents.document_explanation import explain_document
from app.documents.ocr import OCRResult, ocr_available

RISKY_CONTRACT_TEXT = (
    "근로계약서\n"
    "근로시간: 09:00부터 20:00까지\n"
    "임금: 시급 7,000원으로 하며 회사는 임금을 일방적으로 삭감할 수 있다.\n"
    "연장근로 수당은 기본 시급과 동일하게 지급한다.\n"
    "계약 위반 시 근로자는 위약금 500만원을 배상한다.\n"
)

NORMAL_CONTRACT_TEXT = (
    "표준근로계약서\n"
    "근로계약기간: 2026년 1월 1일부터 12월 31일까지\n"
    "근로시간: 09:00부터 18:00까지 휴게시간 12:00부터 13:00\n"
    "임금: 월급 2,300,000원 임금 지급일 매월 10일\n"
    "휴일: 주휴일 일요일 연차 유급휴가 부여\n"
    "연장근로 시 가산수당을 지급한다.\n"
)


def make_contract_image(text: str, rotate: int = 0, blur: bool = False, crop: bool = False) -> bytes:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    image = Image.new("RGB", (1400, 900), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\malgun.ttf", 34)
    for index, line in enumerate(text.strip().split("\n")):
        draw.text((60, 60 + index * 70), line, fill="black", font=font)
    if crop:
        image = image.crop((0, 0, 700, 900))
    if rotate:
        image = image.rotate(rotate, expand=True, fillcolor="white")
    if blur:
        image = image.filter(ImageFilter.GaussianBlur(8))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_scanned_pdf(image_bytes: bytes) -> bytes:
    import fitz
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 100, 595, 500), stream=image_bytes)
    return document.tobytes()


class MockedOCRPipelineTests(unittest.TestCase):
    """Engine-independent behavior of the OCR-fronted document pipeline."""

    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key
        settings.rag_use_sample_documents_for_tests = self.original_flag

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=OCRResult(RISKY_CONTRACT_TEXT, 0.95))
    def test_confident_ocr_feeds_existing_risk_analysis(self, _ocr) -> None:
        result = explain_document(b"png-bytes", "image/png", "contract.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertEqual(result.ocr_confidence, 0.95)
        self.assertEqual(result.document_type, "employment_contract")
        self.assertIn("WARNING", {item.level for item in result.risk_items})
        warning = next(item for item in result.risk_items if item.level == "WARNING")
        self.assertTrue(warning.sources)
        self.assertTrue(result.original_text)

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=OCRResult("주민번호 900101-1234567 근로계약서 임금 월급", 0.9))
    def test_ocr_text_is_redacted_before_analysis(self, _ocr) -> None:
        result = explain_document(b"png-bytes", "image/png", "contract.png", "ko", False)
        self.assertNotIn("900101-1234567", result.original_text)
        self.assertTrue(result.privacy_redacted)

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=OCRResult("흐릿한 글자", 0.31))
    def test_low_confidence_refuses_analysis_and_asks_for_retake(self, _ocr) -> None:
        result = explain_document(b"png-bytes", "image/png", "blurry.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertEqual(result.risk_items, [])
        self.assertEqual(result.key_terms, {})
        self.assertIn("정확하게 읽지 못했습니다", result.summary)
        self.assertTrue(any("촬영" in action for action in result.actions))

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=OCRResult("", 0.0))
    def test_empty_ocr_result_refuses_analysis(self, _ocr) -> None:
        result = explain_document(b"png-bytes", "image/png", "blank.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertIn("정확하게 읽지 못했습니다", result.summary)

    @patch("app.documents.document_explanation.recognize_pdf_bytes", return_value=OCRResult(NORMAL_CONTRACT_TEXT, 0.92))
    def test_scanned_pdf_uses_ocr_when_pypdf_finds_no_text(self, _ocr) -> None:
        result = explain_document(b"%PDF-fake-scan", "application/pdf", "scan.pdf", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertEqual(result.document_type, "employment_contract")
        self.assertNotIn("WARNING", {item.level for item in result.risk_items})

    @patch("app.documents.document_explanation.recognize_image_bytes", return_value=None)
    def test_engine_unavailable_keeps_legacy_consent_path(self, _ocr) -> None:
        with self.assertRaises(PermissionError):
            explain_document(b"png-bytes", "image/png", "contract.png", "ko", False)


@unittest.skipUnless(ocr_available(), "PaddleOCR engine is not installed")
class RealOCRIntegrationTests(unittest.TestCase):
    """Real engine on generated contract images; no external API involved."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.original_key = settings.openai_api_key
        cls.original_flag = settings.rag_use_sample_documents_for_tests
        settings.openai_api_key = None
        settings.rag_use_sample_documents_for_tests = True

    @classmethod
    def tearDownClass(cls) -> None:
        settings.openai_api_key = cls.original_key
        settings.rag_use_sample_documents_for_tests = cls.original_flag

    def test_normal_contract_image_is_read_and_classified(self) -> None:
        result = explain_document(make_contract_image(NORMAL_CONTRACT_TEXT), "image/png", "normal.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertGreaterEqual(result.ocr_confidence or 0, settings.ocr_min_confidence)
        self.assertEqual(result.document_type, "employment_contract")
        self.assertNotIn("WARNING", {item.level for item in result.risk_items})

    def test_risky_contract_image_triggers_risk_items_with_sources(self) -> None:
        result = explain_document(make_contract_image(RISKY_CONTRACT_TEXT), "image/png", "risky.png", "ko", False)
        self.assertTrue(result.ocr_used)
        levels = {item.level for item in result.risk_items}
        self.assertIn("WARNING", levels)
        warning = next(item for item in result.risk_items if item.level == "WARNING")
        self.assertTrue(warning.sources)

    def test_rotated_image_still_reads(self) -> None:
        result = explain_document(make_contract_image(NORMAL_CONTRACT_TEXT, rotate=180), "image/png", "rotated.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertEqual(result.document_type, "employment_contract")

    def test_cropped_image_returns_without_crash(self) -> None:
        result = explain_document(make_contract_image(NORMAL_CONTRACT_TEXT, crop=True), "image/png", "cropped.png", "ko", False)
        self.assertTrue(result.ocr_used)

    def test_blurry_image_is_refused_or_degraded_safely(self) -> None:
        result = explain_document(make_contract_image(RISKY_CONTRACT_TEXT, blur=True), "image/png", "blurry.png", "ko", False)
        self.assertTrue(result.ocr_used)
        if "정확하게 읽지 못했습니다" not in result.summary:
            self.assertGreaterEqual(result.ocr_confidence or 0, settings.ocr_min_confidence)

    def test_blank_image_is_refused(self) -> None:
        from PIL import Image
        buffer = io.BytesIO()
        Image.new("RGB", (1000, 800), "white").save(buffer, format="PNG")
        result = explain_document(buffer.getvalue(), "image/png", "blank.png", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertIn("정확하게 읽지 못했습니다", result.summary)

    def test_scanned_pdf_is_ocred(self) -> None:
        result = explain_document(make_scanned_pdf(make_contract_image(RISKY_CONTRACT_TEXT)), "application/pdf", "scan.pdf", "ko", False)
        self.assertTrue(result.ocr_used)
        self.assertEqual(result.document_type, "employment_contract")


if __name__ == "__main__":
    unittest.main()
