# 문서 분석의 DB RAG 근거 연결(전량 로드 금지·장애 강등)을 검증하는 테스트 파일
"""DB-backed RAG evidence for document review (candidate-set search path).

Mock-based tests simulate PostgreSQL candidate queries and prove that
(1) evidence comes from DB candidates via the shared search service,
(2) SAMPLE_DOCUMENTS are never a silent fallback, (3) pending/inactive rows
are excluded, (4) the LLM receives the OFFICIAL_EVIDENCE block, and (5)
model-invented URLs are stripped. The integration class runs against the live
dev PostgreSQL when available. No OpenAI API is called anywhere.
"""
import json
import unittest
from unittest.mock import patch

import app.retrieval.rag as rag
from app.core.config import settings
from app.documents.document_explanation import analyze_document_risks, explain_document
from app.retrieval.rag import SAMPLE_DOCUMENTS

from documents.test_document_risks import DETAILED_RISKY_CONTRACT

DB_ROWS = [(document, chunk.chunk_id, chunk.text, chunk.chunk_index) for document, chunks in SAMPLE_DOCUMENTS for chunk in chunks]


def make_fake_fetch(rows):
    """Simulates database.fetch_lexical_candidates over the given DB rows."""

    def fake_fetch(query_tokens, category, limit):
        token_set = set(query_tokens)
        scored = []
        for document, chunk_id, text, index in rows:
            if category and document.category != category:
                continue
            if not document.active or document.status not in {"active", "approved", "fetch_failed"}:
                continue
            overlap = len(rag._tokens(f"{document.title} {document.publisher} {text}") & token_set)
            if overlap:
                scored.append((overlap, (document, chunk_id, text, index)))
        scored.sort(key=lambda item: -item[0])
        return [row for _, row in scored[:limit]]

    return fake_fetch


def rows_with_pending_minimum_wage():
    notice = next(document for document, _ in SAMPLE_DOCUMENTS if document.document_id == "minimumwage-2026-notice")
    pending = notice.model_copy(update={"status": "review_pending", "active": False, "version": "2", "original_text": "9999년 적용 최저임금 고시 기준은 시간급 99,999원이다."})
    return DB_ROWS + [(pending, "minimumwage-2026-notice:pending:0", pending.original_text, 0)]


class DbEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_flag = settings.rag_use_sample_documents_for_tests
        settings.rag_use_sample_documents_for_tests = False  # samples must NOT be needed
        rag._search_cache.clear()

    def tearDown(self) -> None:
        settings.rag_use_sample_documents_for_tests = self.original_flag
        rag._search_cache.clear()

    def run_analysis(self, rows):
        with patch("app.infra.database.database_available", return_value=True), \
             patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(rows)), \
             patch("app.infra.database.search_rag_vectors", return_value=None), \
             patch("app.infra.database.load_rag_chunks", side_effect=AssertionError("full corpus load must not happen during search")):
            return analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")

    def test_risk_sources_come_from_database_rows(self) -> None:
        items = self.run_analysis(DB_ROWS)
        wage = next(item for item in items if item.detected_value == "9500")
        self.assertEqual(wage.level, "WARNING")
        self.assertEqual(wage.sources[0].document_id, "minimumwage-2026-notice")
        overtime = next(item for item in items if "가산수당" in item.title)
        self.assertIn("moel-overtime-premium-standard", {source.document_id for source in overtime.sources})
        cut = next(item for item in items if "삭감" in item.title)
        self.assertIn("moel-wage-cut-penalty-prohibition", {source.document_id for source in cut.sources})
        annual = next(item for item in items if "연차" in item.title)
        self.assertIn("moel-annual-leave-standard", {source.document_id for source in annual.sources})

    def test_full_chunk_loader_is_never_called_during_search(self) -> None:
        items = self.run_analysis(DB_ROWS)  # run_analysis raises if load_rag_chunks is touched
        self.assertTrue(items)

    def test_review_pending_versions_are_excluded(self) -> None:
        items = self.run_analysis(rows_with_pending_minimum_wage())
        wage = next(item for item in items if item.detected_value == "9500")
        self.assertEqual(wage.official_value, "10320")
        self.assertNotIn("99,999", wage.official_standard)

    def test_db_outage_degrades_without_sample_fallback(self) -> None:
        with patch("app.infra.database.database_available", return_value=False):
            items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        self.assertTrue(items)
        for item in items:
            self.assertNotEqual(item.level, "WARNING", item.title)
            self.assertEqual(item.sources, [], item.title)
        outage = next(item for item in items if "삭감" in item.title)
        self.assertIn("일시적으로 접근할 수 없어", outage.problem)

    def test_source_metadata_matches_db_documents(self) -> None:
        items = self.run_analysis(DB_ROWS)
        wage = next(item for item in items if item.detected_value == "9500")
        notice = next(document for document, _ in SAMPLE_DOCUMENTS if document.document_id == "minimumwage-2026-notice")
        source = wage.sources[0]
        self.assertEqual(source.title, notice.title)
        self.assertEqual(source.publisher, notice.publisher)
        self.assertEqual(source.url, notice.source_url)
        self.assertTrue(source.trust_level)
        self.assertGreater(source.authority_score, 0)

    def test_query_budget_limits_search_calls(self) -> None:
        original = settings.rag_document_max_queries
        settings.rag_document_max_queries = 2
        try:
            items = self.run_analysis(DB_ROWS)
            self.assertLessEqual(sum(1 for item in items if item.sources), 2)
        finally:
            settings.rag_document_max_queries = original

    def test_llm_receives_official_evidence_block(self) -> None:
        class CapturingResponses:
            params = None

            def create(self, **kwargs):
                CapturingResponses.params = kwargs
                payload = {"summary": "요약", "key_points": [], "actions": [], "deadlines": [], "cautions": [], "related_guide_ids": []}
                return type("Response", (), {"output_text": json.dumps(payload)})()

        class CapturingClient:
            def __init__(self, **kwargs) -> None:
                self.responses = CapturingResponses()

        original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"
        try:
            with patch("app.infra.database.database_available", return_value=True), \
                 patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS)), \
                 patch("app.infra.database.search_rag_vectors", return_value=None):
                explain_document(DETAILED_RISKY_CONTRACT.encode(), "text/plain", "contract.txt", "ko", False, CapturingClient)
        finally:
            settings.openai_api_key = original_key
        serialized = json.dumps(CapturingResponses.params["input"], ensure_ascii=False)
        self.assertIn("[UPLOADED_DOCUMENT]", serialized)
        self.assertIn("[OFFICIAL_EVIDENCE]", serialized)
        self.assertIn("2026년 적용 최저임금 고시", serialized)
        self.assertIn("OFFICIAL_EVIDENCE", CapturingResponses.params["instructions"])

    def test_model_invented_urls_are_stripped_from_response(self) -> None:
        class FakeUrlResponses:
            def create(self, **kwargs):
                payload = {"summary": "자세한 내용은 http://fake.invalid/law 를 참고하세요.", "key_points": ["기준: https://made-up.example.com"], "actions": [], "deadlines": [], "cautions": [], "related_guide_ids": []}
                return type("Response", (), {"output_text": json.dumps(payload)})()

        class FakeUrlClient:
            def __init__(self, **kwargs) -> None:
                self.responses = FakeUrlResponses()

        original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"
        try:
            with patch("app.infra.database.database_available", return_value=True), \
                 patch("app.infra.database.fetch_lexical_candidates", side_effect=make_fake_fetch(DB_ROWS)), \
                 patch("app.infra.database.search_rag_vectors", return_value=None):
                result = explain_document(DETAILED_RISKY_CONTRACT.encode(), "text/plain", "contract.txt", "ko", False, FakeUrlClient)
        finally:
            settings.openai_api_key = original_key
        self.assertNotIn("http", result.summary)
        self.assertNotIn("http", " ".join(result.key_points))
        for item in result.risk_items:
            for source in item.sources:
                self.assertNotIn("fake.invalid", source.url)
                self.assertNotIn("made-up", source.url)


class RealDatabaseIntegrationTests(unittest.TestCase):
    """Runs against the live dev PostgreSQL (docker compose db) when reachable."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.original_enabled = settings.database_enabled
        cls.original_flag = settings.rag_use_sample_documents_for_tests
        settings.database_enabled = True
        settings.rag_use_sample_documents_for_tests = False
        from app.infra.database import database_available
        if not database_available():
            settings.database_enabled = cls.original_enabled
            raise unittest.SkipTest("PostgreSQL is not reachable")
        rag._search_cache.clear()

    @classmethod
    def tearDownClass(cls) -> None:
        settings.database_enabled = cls.original_enabled
        settings.rag_use_sample_documents_for_tests = cls.original_flag
        rag._search_cache.clear()

    def test_contract_review_uses_postgres_documents(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        wage = next(item for item in items if item.detected_value == "9500")
        self.assertEqual(wage.level, "WARNING")
        self.assertEqual(wage.official_value, "10320")
        self.assertEqual(wage.sources[0].document_id, "minimumwage-2026-notice")
        self.assertIn("시간급 10,320원", wage.official_standard)

    def test_overtime_and_wage_cut_link_postgres_evidence(self) -> None:
        items = analyze_document_risks(DETAILED_RISKY_CONTRACT, "employment_contract")
        sourced = {source.document_id for item in items for source in item.sources}
        self.assertIn("moel-overtime-premium-standard", sourced)
        self.assertIn("moel-wage-cut-penalty-prohibition", sourced)

    def test_review_pending_rows_are_excluded_by_sql(self) -> None:
        from app.infra.database import connection
        from app.retrieval.rag import _tokens
        tokens = list(_tokens("임시 검증 전용 문서 최저임금"))
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO rag_documents (document_id,title,publisher,category,original_text,source_url,language,collected_at,verified_at,version,content_hash,active,status) VALUES ('pending-probe','임시 검증 전용 문서','고용노동부','labor','임시 검증 전용 본문','https://www.moel.go.kr/','ko',CURRENT_DATE,CURRENT_DATE,'1','probe-hash',false,'review_pending') ON CONFLICT (document_id) DO NOTHING")
            cursor.execute("INSERT INTO rag_chunks (chunk_id,document_id,chunk_index,text,content_hash,active,search_tokens) VALUES ('pending-probe:0','pending-probe',0,'임시 검증 전용 본문','probe-hash',true,%s) ON CONFLICT (chunk_id) DO NOTHING", (tokens,))
        try:
            rag._search_cache.clear()
            results = rag.search_rag_db("임시 검증 전용 문서", category="labor")
            self.assertIsNotNone(results)
            self.assertNotIn("pending-probe", {chunk.document.document_id for chunk, _ in results})
        finally:
            with connection() as conn, conn.cursor() as cursor:
                cursor.execute("DELETE FROM rag_documents WHERE document_id='pending-probe'")


if __name__ == "__main__":
    unittest.main()
