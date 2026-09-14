# 실 PostgreSQL 승인 워크플로(review_pending→approve→임베딩→검색 노출, reject→비활성)를 검증하는 테스트 파일
"""Real-database workflow tests. Auto-skip when PostgreSQL is unavailable.

Uses a synthetic crawled document with a crawl-test- prefix; rows are cleaned up
in tearDown so repeated runs stay idempotent."""
import unittest

from app.core.config import settings
from app.infra.database import (approve_rag_version, connection, database_available, get_rag_document_summary,
                          initialize_database, list_pending_rag_versions, rag_index_version, reject_rag_version,
                          save_crawled_document_pending)
from app.retrieval.rag import content_hash, index_approved_document, register_document, search_rag_db
import app.retrieval.rag as rag

DB_READY = settings.database_enabled and database_available()

DOC_ID = "crawl-test-workflow-0001"
BODY = ("전북 지역 외국인 근로자를 위한 가상 크롤링 검증 문서입니다. 크롤러 승인 워크플로 테스트 전용 텍스트로, "
        "심야근로검증키워드 항목과 절차를 설명합니다. 이 문서는 테스트 후 삭제됩니다. " * 3)


def _cleanup() -> None:
    with connection() as conn, conn.cursor() as cursor:
        cursor.execute("DELETE FROM rag_version_chunks WHERE version_id IN (SELECT version_id FROM rag_document_versions WHERE document_id LIKE 'crawl-test-%')")
        cursor.execute("DELETE FROM rag_document_versions WHERE document_id LIKE 'crawl-test-%'")
        cursor.execute("DELETE FROM rag_chunks WHERE document_id LIKE 'crawl-test-%'")
        cursor.execute("DELETE FROM rag_documents WHERE document_id LIKE 'crawl-test-%'")
        cursor.execute("DELETE FROM rag_update_audit WHERE document_id LIKE 'crawl-test-%'")


@unittest.skipUnless(DB_READY, "PostgreSQL is not available")
class RealDbCrawlWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        initialize_database()
        _cleanup()

    def tearDown(self) -> None:
        _cleanup()
        rag._search_cache.clear()

    def register_pending(self, text: str = BODY, version: str = "1", previous: str | None = None):
        document, chunks = register_document(
            document_id=DOC_ID, title="크롤러 워크플로 검증 문서", publisher="고용노동부", category="labor",
            text=text, source_url="https://www.moel.go.kr/faq/faqView.do?seqRepeat=999999",
            version=version, active=False, status="review_pending", previous_version_id=previous)
        rows = [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks]
        saved = save_crawled_document_pending(document, rows, quality_score=0.85)
        return document, saved

    def test_pending_document_is_invisible_until_approved_then_searchable(self) -> None:
        document, saved = self.register_pending()
        self.assertTrue(saved)
        # 1) review_pending: not searchable
        rag._search_cache.clear()
        results = search_rag_db("심야근로검증키워드", category="labor") or []
        self.assertNotIn(DOC_ID, [chunk.document.document_id for chunk, _ in results])
        # 2) queue lists it with quality metadata
        pending = list_pending_rag_versions() or []
        entry = next(item for item in pending if item["document_id"] == DOC_ID)
        self.assertEqual(entry["crawl_quality_score"], 0.85)
        self.assertTrue(entry["is_new_document"])
        self.assertTrue(entry["url_specific"])
        # 3) approve -> embedding -> index version bump -> searchable
        before_version = rag_index_version()
        approved_id = approve_rag_version(document.version_id, "테스트 관리자", "통합 테스트 승인")
        self.assertEqual(approved_id, DOC_ID)
        summary = index_approved_document(DOC_ID)
        self.assertEqual(summary["failed"], 0)
        self.assertGreaterEqual(summary["chunks"], 1)
        self.assertNotEqual(rag_index_version(), before_version)
        current = get_rag_document_summary(DOC_ID)
        self.assertEqual(current["status"], "active")
        rag._search_cache.clear()
        results = search_rag_db("심야근로검증키워드", category="labor") or []
        self.assertIn(DOC_ID, [chunk.document.document_id for chunk, _ in results])

    def test_rejected_document_stays_inactive(self) -> None:
        document, saved = self.register_pending()
        self.assertTrue(saved)
        self.assertTrue(reject_rag_version(document.version_id, "테스트 관리자", "품질 미달"))
        current = get_rag_document_summary(DOC_ID)
        self.assertEqual(current["status"], "review_pending")  # 문서 행은 승인 전 상태 그대로, active 아님
        rag._search_cache.clear()
        results = search_rag_db("심야근로검증키워드", category="labor") or []
        self.assertNotIn(DOC_ID, [chunk.document.document_id for chunk, _ in results])
        pending = list_pending_rag_versions() or []
        self.assertNotIn(DOC_ID, [item["document_id"] for item in pending])

    def test_changed_recrawl_creates_second_pending_version_without_touching_active(self) -> None:
        document, _ = self.register_pending()
        approve_rag_version(document.version_id, "테스트 관리자", "1차 승인")
        index_approved_document(DOC_ID)
        current = get_rag_document_summary(DOC_ID)
        # simulate a changed re-crawl -> new pending version
        from app.infra.database import save_pending_rag_version
        changed, chunks = register_document(
            document_id=DOC_ID, title="크롤러 워크플로 검증 문서", publisher="고용노동부", category="labor",
            text=BODY + " 개정된 조항이 추가되었습니다.", source_url="https://www.moel.go.kr/faq/faqView.do?seqRepeat=999999",
            version="2", active=False, status="review_pending", previous_version_id=current["version_id"])
        rows = [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks]
        self.assertTrue(save_pending_rag_version(changed, rows, quality_score=0.9))
        # active version still serves while the change waits for review
        self.assertEqual(get_rag_document_summary(DOC_ID)["status"], "active")
        rag._search_cache.clear()
        results = search_rag_db("심야근로검증키워드", category="labor") or []
        self.assertIn(DOC_ID, [chunk.document.document_id for chunk, _ in results])
        pending = list_pending_rag_versions() or []
        self.assertIn(DOC_ID, [item["document_id"] for item in pending])


if __name__ == "__main__":
    unittest.main()
