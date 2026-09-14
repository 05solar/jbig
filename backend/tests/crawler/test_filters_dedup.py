# 파서·필터·중복제거(본문 추출, 무관/짧은 문서 거부, URL/해시 중복, 품질 점수)를 검증하는 테스트 파일
"""Parser/filter/dedup unit tests. Fully offline."""
import unittest

from app.core.config import settings
from app.crawler.base import CrawlCandidate, SourceSpec
from app.crawler.dedup import DedupRegistry, canonical_url, content_fingerprint
from app.crawler.filters import is_allowed_detail_url, is_denied_url, is_irrelevant, quality_score
from app.crawler.parser import detect_language, extract_published_at, parse_page
from app.retrieval.rag import is_specific_source_url

SPEC = SourceSpec(key="moel-faq", domain="www.moel.go.kr", publisher="고용노동부", category="labor", detail_patterns=(r"/faq/faqView\.do\?[^\"'\s]*seqRepeat=\d+",))

ARTICLE_HTML = """
<html><head><title>고용노동부</title></head><body>
<div class="gnb"><a href="/menu1">정책자료</a><a href="/menu2">민원</a></div>
<div id="contents">
  <h2>임금체불 진정은 어떻게 하나요?</h2>
  <p>임금을 지급받지 못한 근로자는 사업장 관할 지방고용노동관서에 진정을 제기할 수 있습니다.
  진정은 고용노동부 노동포털을 통해 온라인으로 제출하거나 방문하여 접수할 수 있습니다.
  등록일 : 2026.02.10</p>
</div>
<footer><div class="copyright">고용노동부 all rights reserved</div></footer>
</body></html>
"""


class ParserTests(unittest.TestCase):
    def test_body_extraction_strips_menu_and_footer(self) -> None:
        page = parse_page(ARTICLE_HTML, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        self.assertIn("지방고용노동관서에 진정을", page.body)
        self.assertNotIn("all rights reserved", page.body)
        self.assertNotIn("메뉴", page.body)
        self.assertEqual(page.title, "임금체불 진정은 어떻게 하나요?")

    def test_published_date_is_detected(self) -> None:
        self.assertEqual(extract_published_at("등록일 : 2026.02.10"), "2026-02-10")
        self.assertEqual(extract_published_at("2025-12-01 고시"), "2025-12-01")
        self.assertIsNone(extract_published_at("연락처 1350"))

    def test_language_detection(self) -> None:
        self.assertEqual(detect_language("외국인 근로자의 임금"), "ko")
        self.assertEqual(detect_language("Minimum wage guidance for foreign workers in Korea"), "en")
        self.assertEqual(detect_language("Tôi muốn gia hạn thời gian lưu trú của mình"), "vi")

    def test_list_links_are_resolved_absolute(self) -> None:
        html = '<a href="/faq/faqView.do?seqRepeat=7">상세</a>'
        page = parse_page(html, "https://www.moel.go.kr/faq/faqList.do")
        self.assertIn(("https://www.moel.go.kr/faq/faqView.do?seqRepeat=7", "상세"), page.links)


class FilterTests(unittest.TestCase):
    def test_detail_url_is_recognized(self) -> None:
        self.assertTrue(is_allowed_detail_url("https://www.moel.go.kr/faq/faqView.do?seqRepeat=12", SPEC))
        self.assertFalse(is_allowed_detail_url("https://www.moel.go.kr/faq/faqList.do", SPEC))
        self.assertFalse(is_allowed_detail_url("https://1350.moel.go.kr/faqview.do?id=1", SPEC))  # other domain

    def test_generic_homepage_root_is_not_a_detail_url(self) -> None:
        self.assertFalse(is_specific_source_url("https://www.moel.go.kr/"))
        self.assertFalse(is_allowed_detail_url("https://www.moel.go.kr/", SPEC))

    def test_denied_paths_are_filtered(self) -> None:
        self.assertTrue(is_denied_url("https://www.moel.go.kr/recruit/list.do?id=3"))
        self.assertTrue(is_denied_url("https://www.moel.go.kr/photo/gallery.do?id=3"))
        self.assertFalse(is_denied_url("https://www.moel.go.kr/faq/faqView.do?seqRepeat=3"))

    def test_irrelevant_page_is_rejected(self) -> None:
        self.assertTrue(is_irrelevant("2026년 공무직 채용 공고", "지원서 접수 기간과 면접 일정 안내" * 30, "labor"))
        self.assertTrue(is_irrelevant("기관 소개", "우리 위원회의 연혁과 조직을 소개합니다" * 30, "labor"))
        self.assertFalse(is_irrelevant("임금체불 진정 방법", "임금을 받지 못한 근로자는 진정을 제기할 수 있습니다", "labor"))

    def test_quality_score_orders_good_documents_higher(self) -> None:
        good = CrawlCandidate(spec=SPEC, url="https://www.moel.go.kr/faq/faqView.do?seqRepeat=1", canonical_url="https://www.moel.go.kr/faq/faqView.do?seqRepeat=1", title="임금체불 진정 절차 안내", body="임금 근로 수당 진정 절차 설명. " * 60, published_at="2026-02-10")
        bad = CrawlCandidate(spec=SPEC, url="https://www.moel.go.kr/", canonical_url="https://www.moel.go.kr", title="홈", body="메뉴\n" * 40)
        self.assertGreater(quality_score(good), quality_score(bad))
        self.assertGreaterEqual(quality_score(good), 0.7)
        self.assertLessEqual(quality_score(bad), 0.4)

    def test_short_content_threshold_setting_is_used(self) -> None:
        self.assertGreaterEqual(settings.crawler_min_content_chars, 300)


class DedupTests(unittest.TestCase):
    def test_canonical_url_strips_session_and_tracking(self) -> None:
        url = "https://www.minimumwage.go.kr/customer/faq/view.do;jsessionid=ABC123?b=2&a=1&utm_source=x"
        self.assertEqual(canonical_url(url), "https://www.minimumwage.go.kr/customer/faq/view.do?a=1&b=2")

    def test_query_and_path_are_preserved(self) -> None:
        url = "https://1350.moel.go.kr/faqview.do?id=1000001402"
        self.assertEqual(canonical_url(url), url)

    def test_duplicate_url_is_rejected(self) -> None:
        registry = DedupRegistry()
        self.assertIsNone(registry.check("https://a.go.kr/v.do?id=1", "제목", "본문 내용입니다"))
        self.assertEqual(registry.check("https://a.go.kr/v.do?id=1", "제목", "본문 내용입니다"), "duplicate_url")

    def test_duplicate_content_hash_is_rejected(self) -> None:
        registry = DedupRegistry()
        registry.check("https://a.go.kr/v.do?id=1", "제목 A", "같은 본문 내용")
        self.assertEqual(registry.check("https://a.go.kr/v.do?id=2", "제목 B", "같은   본문\n내용"), "duplicate_content")

    def test_near_identical_body_with_same_title_is_rejected(self) -> None:
        registry = DedupRegistry()
        base = ("외국인등록 신청 절차와 필요서류를 안내합니다. 여권과 통합신청서, 체류자격 입증서류, 수수료를 준비하여 "
                "관할 출입국외국인관서에 방문 예약 후 신청해야 하며 처리 기간과 자세한 문의는 하이코리아 또는 1345 상담센터에서 확인할 수 있습니다.")
        registry.check("https://a.go.kr/v.do?id=1", "외국인등록 안내", base)
        self.assertEqual(registry.check("https://a.go.kr/v.do?id=3", "외국인 등록 안내!", base + "추가 한 줄"), "duplicate_content")

    def test_different_documents_pass(self) -> None:
        registry = DedupRegistry()
        registry.check("https://a.go.kr/v.do?id=1", "외국인등록 안내", "외국인등록 신청 절차 안내" * 10)
        self.assertIsNone(registry.check("https://a.go.kr/v.do?id=2", "체류기간 연장", "체류기간 연장 허가 신청 방법" * 10))

    def test_content_fingerprint_ignores_whitespace(self) -> None:
        self.assertEqual(content_fingerprint("가 나\n다"), content_fingerprint("가나다"))


if __name__ == "__main__":
    unittest.main()
