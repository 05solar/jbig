# 크롤 파이프라인(목록→상세→review_pending 등록, active 직접 생성 금지, 갱신/승인/색인 흐름)을 검증하는 테스트 파일
"""Pipeline and registration-workflow tests with fake transport and patched DB."""
import unittest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.crawler.base import SourceSpec
from app.crawler.fetcher import Fetcher
from app.crawler.pipeline import document_id_for, run_crawl

SPEC = SourceSpec(
    key="moel-faq-test", domain="www.moel.go.kr", publisher="고용노동부", category="labor",
    list_urls=("https://www.moel.go.kr/faq/faqList.do?cvlcCtgCd=MC01",),
    detail_patterns=(r"/faq/faqView\.do\?[^\"'\s]*seqRepeat=\d+",),
)

LIST_HTML = """
<html><body><div id="contents">
<a href="/faq/faqView.do?seqRepeat=1">임금체불 진정</a>
<a href="/faq/faqView.do?seqRepeat=2">짧은 글</a>
<a href="/faq/faqView.do?seqRepeat=3">채용 공고</a>
<a href="/faq/faqView.do?seqRepeat=4&utm_source=x">임금체불 진정(중복)</a>
<a href="/recruit/notice.do?id=9">채용 게시판</a>
<a href="https://blog.example.com/tip">외부 블로그</a>
</div></body></html>
"""

GOOD_BODY = ("임금을 지급받지 못한 근로자는 사업장 관할 지방고용노동관서에 임금체불 진정을 제기할 수 있습니다. "
             "진정서에는 근무 기간, 미지급 임금 내역을 적고 근로계약서와 급여명세서를 첨부합니다. "
             "고용노동부 노동포털을 통한 온라인 접수와 방문 접수가 모두 가능하며 자세한 내용은 1350으로 문의합니다. "
             "체불 임금과 지연이자는 사실관계 확인 후 산정되며 필요한 경우 무료 법률구조 지원도 안내받을 수 있습니다. "
             "사업주가 지급을 거부하는 경우 근로감독관의 조사 절차가 진행되고, 조사 결과에 따라 시정지시 또는 사법처리가 이루어질 수 있습니다. "
             "퇴직 근로자는 퇴직일로부터 임금 지급 기한이 지난 뒤에도 지급되지 않으면 동일하게 진정을 제기할 수 있습니다.")


def detail(title: str, body: str) -> tuple[int, str, bytes, None]:
    html = f'<html><body><div id="contents"><h2>{title}</h2><p>{body}</p><p>등록일 : 2026.03.02</p></div></body></html>'
    return (200, "text/html", html.encode("utf-8"), None)


def build_pages() -> dict:
    return {
        "https://www.moel.go.kr/faq/faqList.do?cvlcCtgCd=MC01": (200, "text/html", LIST_HTML.encode("utf-8"), None),
        "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1": detail("임금체불 진정은 어떻게 하나요?", GOOD_BODY),
        "https://www.moel.go.kr/faq/faqView.do?seqRepeat=2": detail("짧은 안내", "임금 관련 짧은 글."),
        "https://www.moel.go.kr/faq/faqView.do?seqRepeat=3": detail("2026년 공무직 채용 공고", "지원서 접수 기간과 면접 일정을 안내합니다. " * 20),
        "https://www.moel.go.kr/faq/faqView.do?seqRepeat=4": detail("임금체불 진정은 어떻게 하나요?", GOOD_BODY),
    }


def make_transport(pages: dict):
    import urllib.error

    def transport(url: str):
        entry = pages.get(url)
        if entry is None:
            raise urllib.error.HTTPError(url, 404, "not found", None, None)
        status, content_type, body, final_url = entry
        return status, content_type, body, final_url or url
    return transport


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_delay = settings.crawler_request_delay_ms
        settings.crawler_request_delay_ms = 0

    def tearDown(self) -> None:
        settings.crawler_request_delay_ms = self.original_delay

    def run_dry(self):
        fetcher = Fetcher(transport=make_transport(build_pages()))
        return run_crawl((SPEC,), dry_run=True, fetcher=fetcher)

    def test_dry_run_collects_only_relevant_unique_candidates(self) -> None:
        report, candidates = self.run_dry()
        self.assertEqual([candidate.title for candidate in candidates], ["임금체불 진정은 어떻게 하나요?"])
        self.assertEqual(report.rejected_short, 1)
        self.assertEqual(report.rejected_irrelevant, 1)
        self.assertEqual(report.rejected_duplicate, 1)
        self.assertEqual(report.accepted_candidates, 1)

    def test_dry_run_writes_nothing(self) -> None:
        with patch("app.infra.database.save_crawled_document_pending") as save_new, \
             patch("app.infra.database.save_pending_rag_version") as save_pending, \
             patch("app.infra.database.save_rag_document") as save_active:
            self.run_dry()
        save_new.assert_not_called()
        save_pending.assert_not_called()
        save_active.assert_not_called()

    def test_detail_source_url_preserves_path_and_query(self) -> None:
        _, candidates = self.run_dry()
        self.assertEqual(candidates[0].canonical_url, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")

    def test_new_document_is_registered_as_review_pending_never_active(self) -> None:
        save_new = MagicMock(return_value=True)
        with patch("app.infra.database.get_rag_document_summary", return_value=None), \
             patch("app.infra.database.save_crawled_document_pending", save_new), \
             patch("app.infra.database.save_rag_document") as save_active, \
             patch("app.retrieval.rag.index_documents") as indexer:
            fetcher = Fetcher(transport=make_transport(build_pages()))
            report, _ = run_crawl((SPEC,), dry_run=False, fetcher=fetcher)
        self.assertEqual(report.new_documents, 1)
        save_active.assert_not_called()
        indexer.assert_not_called()
        document = save_new.call_args.args[0]
        self.assertFalse(document.active)
        self.assertEqual(document.status, "review_pending")
        self.assertEqual(document.source_url, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")

    def test_changed_document_becomes_pending_version(self) -> None:
        current = {"content_hash": "old-hash", "version": "1", "version_id": "doc:1:abc", "status": "active"}
        save_pending = MagicMock(return_value=True)
        with patch("app.infra.database.get_rag_document_summary", return_value=current), \
             patch("app.infra.database.save_pending_rag_version", save_pending), \
             patch("app.infra.database.save_rag_document") as save_active:
            fetcher = Fetcher(transport=make_transport(build_pages()))
            report, _ = run_crawl((SPEC,), dry_run=False, fetcher=fetcher)
        self.assertEqual(report.updated_documents, 1)
        save_active.assert_not_called()
        document = save_pending.call_args.args[0]
        self.assertEqual(document.status, "review_pending")
        self.assertEqual(document.version, "2")
        self.assertEqual(document.previous_version_id, "doc:1:abc")

    def test_unchanged_document_only_updates_checked_at(self) -> None:
        record = MagicMock(return_value=True)
        captured: dict[str, str] = {}

        def capture_hash(document, chunks, quality_score=None):
            captured["hash"] = document.content_hash
            return True

        # First run learns the content hash the pipeline produces for this page.
        with patch("app.infra.database.get_rag_document_summary", return_value=None), \
             patch("app.infra.database.save_crawled_document_pending", side_effect=capture_hash):
            run_crawl((SPEC,), dry_run=False, fetcher=Fetcher(transport=make_transport(build_pages())))
        # Second run sees the same hash -> only checked_at is refreshed (§14).
        with patch("app.infra.database.get_rag_document_summary", return_value={"content_hash": captured["hash"], "version": "1", "version_id": "v1", "status": "active"}), \
             patch("app.infra.database.record_rag_check", record), \
             patch("app.infra.database.save_pending_rag_version") as save_pending:
            report, _ = run_crawl((SPEC,), dry_run=False, fetcher=Fetcher(transport=make_transport(build_pages())))
        self.assertEqual(report.unchanged_documents, 1)
        record.assert_called_once()
        save_pending.assert_not_called()

    def test_document_id_is_deterministic_per_canonical_url(self) -> None:
        first = document_id_for(SPEC, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        second = document_id_for(SPEC, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        other = document_id_for(SPEC, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=9")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertTrue(first.startswith("crawl-moel-faq-test-"))


class ApprovalEmbeddingTests(unittest.TestCase):
    def test_index_approved_document_embeds_and_invalidates_cache(self) -> None:
        import app.retrieval.rag as rag
        rag._search_cache["stale"] = "entry"
        embed_chunks = MagicMock(return_value={"chunks": 2, "embedded": 2, "failed": 0})
        with patch("app.infra.database.embed_document_chunks", embed_chunks), \
             patch("app.retrieval.embedding_service.signature", return_value="local:test-model"), \
             patch("app.retrieval.embedding_service.embed_texts", return_value=[[0.1], [0.2]]):
            summary = rag.index_approved_document("crawl-doc-1")
        self.assertEqual(summary["embedded"], 2)
        embed_chunks.assert_called_once()
        self.assertEqual(embed_chunks.call_args.args[0], "crawl-doc-1")
        self.assertEqual(embed_chunks.call_args.args[3], "local:test-model")
        self.assertEqual(rag._search_cache, {})

    def test_table_chunks_are_not_embedded(self) -> None:
        from app.retrieval.rag import is_low_semantic_chunk
        table = "\n".join(["전주시가족센터", "063-243-0333", "전주", "완주군가족센터", "063-231-1037", "완주", "진안군가족센터", "063-433-4888", "진안", "장수군가족센터", "063-352-3362", "장수"])
        prose = ("질의\n부당해고 구제절차\n답변\n" + "근로기준법 제23조에 따라 사용자는 정당한 이유 없이 근로자를 해고하지 못하며, "
                 "부당하게 해고된 근로자는 노동위원회에 구제신청을 할 수 있습니다. " * 4)
        self.assertTrue(is_low_semantic_chunk(table))
        self.assertFalse(is_low_semantic_chunk(prose))

    def test_none_provider_still_fills_search_tokens(self) -> None:
        import app.retrieval.rag as rag
        captured = {}

        def fake_embed_chunks(document_id, embed, tokenizer, signature):
            captured["vectors"] = embed(["텍스트"])
            captured["signature"] = signature
            return {"chunks": 1, "embedded": 0, "failed": 1}

        with patch("app.infra.database.embed_document_chunks", side_effect=fake_embed_chunks):
            original = settings.rag_embedding_provider
            settings.rag_embedding_provider = "none"
            try:
                rag.index_approved_document("crawl-doc-2")
            finally:
                settings.rag_embedding_provider = original
        self.assertIsNone(captured["vectors"])
        self.assertEqual(captured["signature"], "none")


if __name__ == "__main__":
    unittest.main()
