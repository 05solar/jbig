# 원문 변경 감지 워크플로를 검증하는 테스트 파일
import unittest
from unittest.mock import patch

from app.core.config import settings
from app.retrieval.rag import content_hash, register_document, source_from_chunk, trust_for_document
from app.retrieval.updates import FetchResult, _normalize_html, check_source_updates, next_version, summarize_diff


def target(text: str = "기존 공식 문서 내용") -> dict[str, str]:
    return {"document_id": "doc", "title": "공식 안내", "publisher": "고용노동부", "category": "labor", "source_url": "https://www.moel.go.kr/guide", "content_hash": content_hash(text), "version": "1", "version_id": "doc:1:old", "document_type": "guide", "language": "ko", "verified_at": "2026-09-12", "effective_from": "2026-01-01"}


class UpdateTests(unittest.TestCase):
    def test_next_version(self):
        self.assertEqual(next_version("1"), "2")
        self.assertEqual(next_version("2026-spring"), "2026-spring-updated")

    def test_diff_summary_is_bounded_and_shows_changed_lines(self):
        summary = summarize_diff("첫 번째 줄\n같은 줄", "첫 번째 줄\n바뀐 줄")
        self.assertIn("바뀐 줄", summary)

    @patch("app.retrieval.updates.record_rag_check")
    @patch("app.retrieval.updates.save_pending_rag_version")
    def test_unchanged_source_only_updates_check_time(self, save_pending, record_check):
        old = target()
        result = check_source_updates(fetcher=lambda _: FetchResult(old["source_url"], "기존 공식 문서 내용", "text/html", "now"), targets=[old])
        self.assertEqual(result, {"checked": 1, "unchanged": 1, "changed": 0, "failed": 0, "duplicates": 0})
        save_pending.assert_not_called()
        record_check.assert_called_once()

    @patch("app.retrieval.updates.record_rag_check")
    @patch("app.retrieval.updates.save_pending_rag_version", return_value=True)
    def test_changed_source_creates_pending_version(self, save_pending, record_check):
        old = target()
        result = check_source_updates(fetcher=lambda _: FetchResult(old["source_url"], "변경된 공식 문서 내용", "text/html", "now"), targets=[old])
        self.assertEqual(result["changed"], 1)
        pending_document = save_pending.call_args.args[0]
        self.assertEqual(pending_document.status, "review_pending")
        self.assertEqual(pending_document.version, "2")
        self.assertEqual(pending_document.previous_version_id, "doc:1:old")

    @patch("app.retrieval.updates.record_rag_check")
    @patch("app.retrieval.updates.save_pending_rag_version", return_value=False)
    def test_repeated_changed_source_is_not_duplicated(self, save_pending, _record_check):
        old = target()
        result = check_source_updates(fetcher=lambda _: FetchResult(old["source_url"], "변경된 공식 문서 내용", "text/html", "now"), targets=[old])
        self.assertEqual(result["duplicates"], 1)

    @patch("app.retrieval.updates.record_rag_check")
    def test_fetch_failure_preserves_existing_document(self, record_check):
        old = target()
        def fail(_):
            raise TimeoutError("source timeout")
        result = check_source_updates(fetcher=fail, targets=[old])
        self.assertEqual(result["failed"], 1)
        record_check.assert_called_once()
        self.assertIn("TimeoutError", record_check.call_args.kwargs["error"])

    def test_source_contains_version_and_freshness_metadata(self):
        document, chunks = register_document(document_id="doc", title="공식 안내", publisher="고용노동부", category="labor", text="충분히 긴 공식 안내 문서 본문입니다.", source_url="https://www.moel.go.kr/guide", version="3")
        source = source_from_chunk(chunks[0], 0.88)
        self.assertEqual(source.document_version, "3")
        self.assertEqual(source.last_checked_at, document.last_checked_at)
        self.assertEqual(source.freshness_type, "versioned")

    def test_official_law_source_has_high_trust(self):
        document, _ = register_document(document_id="law", title="출입국관리법", publisher="법무부", category="residency", text="법령 원문과 시행일을 확인하는 공식 문서입니다.", source_url="https://law.go.kr/법령", document_type="law")
        score, level, reasons = trust_for_document(document)
        self.assertEqual(level, "high")
        self.assertGreaterEqual(score, 0.8)
        self.assertIn("허용된 공식 도메인", reasons)

    def test_fetch_failed_source_is_marked_for_recheck(self):
        document, _ = register_document(document_id="stale", title="공식 안내", publisher="고용노동부", category="labor", text="오래된 공식 안내 문서의 내용입니다.", source_url="https://www.moel.go.kr/", status="fetch_failed")
        score, level, reasons = trust_for_document(document, "최신성 재확인 필요")
        self.assertLess(score, 0.8)
        self.assertIn("원문 최신성 재확인 필요", reasons)

    def test_update_can_be_disabled(self):
        original = settings.rag_update_enabled
        settings.rag_update_enabled = False
        try:
            self.assertEqual(check_source_updates(targets=[target()]), {"checked": 0, "unchanged": 0, "changed": 0, "failed": 0, "duplicates": 0})
        finally:
            settings.rag_update_enabled = original

    def test_html_normalization_removes_navigation_and_scripts(self):
        text = _normalize_html(b"<nav>Menu</nav><main>Official content</main><script>ignore()</script>")
        self.assertEqual(text, "Official content")


if __name__ == "__main__":
    unittest.main()
