# 문서 설명 기본 계약(마스킹·동의·파일 형식)을 검증하는 테스트 파일
import json
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.documents.document_explanation import explain_document, redact_document_text


class FakeResponses:
    params = None
    def create(self, **kwargs):
        FakeResponses.params = kwargs
        payload = {"summary": "This is a wage notice.", "key_points": ["Payment is delayed."], "actions": ["Keep records."], "deadlines": [], "cautions": ["Get official advice."], "related_guide_ids": ["unpaid-wages"]}
        return type("Response", (), {"output_text": json.dumps(payload)})()


class FakeClient:
    def __init__(self, **kwargs) -> None:
        self.responses = FakeResponses()


class DocumentExplanationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key

    def test_redacts_common_personal_identifiers(self) -> None:
        text, changed = redact_document_text("900101-1234567 test@example.com 010-1234-5678")
        self.assertTrue(changed)
        self.assertNotIn("900101", text)
        self.assertNotIn("test@example.com", text)
        self.assertNotIn("010-1234-5678", text)

    @patch("app.documents.document_explanation.acquire_ai_budget", return_value=True)
    def test_text_document_is_redacted_and_explained(self, _budget) -> None:
        result = explain_document("번호 900101-1234567 임금 지급 안내".encode(), "text/plain", "notice.txt", "ko", False, FakeClient)
        self.assertTrue(result.privacy_redacted)
        self.assertEqual(result.related_guides[0].id, "unpaid-wages")
        serialized_input = json.dumps(FakeResponses.params["input"], ensure_ascii=False)
        self.assertNotIn("900101-1234567", serialized_input)
        self.assertFalse(FakeResponses.params["store"])

    def test_image_requires_explicit_consent(self) -> None:
        with self.assertRaises(PermissionError):
            explain_document(b"fake-image", "image/png", "notice.png", "ko", False, FakeClient)

    def test_rejects_unsupported_file_type(self) -> None:
        with self.assertRaises(ValueError):
            explain_document(b"data", "application/zip", "file.zip", "ko", False, FakeClient)


if __name__ == "__main__":
    unittest.main()
