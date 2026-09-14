# 수집기 예의 규칙(허용 도메인·robots·중복 요청 금지·백오프·콘텐츠 타입)을 검증하는 테스트 파일
"""Fetcher unit tests with an injected offline transport. No real network."""
import unittest
import urllib.error

from app.core.config import settings
from app.crawler.fetcher import Fetcher, SkippedURL


def make_transport(pages: dict):
    calls: list[str] = []

    def transport(url: str):
        calls.append(url)
        entry = pages.get(url)
        if entry is None:
            raise urllib.error.HTTPError(url, 404, "not found", None, None)
        if isinstance(entry, list):  # sequence of responses/errors for retry tests
            entry = entry.pop(0)
        if isinstance(entry, Exception):
            raise entry
        status, content_type, body, final_url = entry
        return status, content_type, body, final_url or url

    return transport, calls


HTML = (200, "text/html", "<html><body>ok</body></html>".encode(), None)


class FetcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_delay = settings.crawler_request_delay_ms
        settings.crawler_request_delay_ms = 0

    def tearDown(self) -> None:
        settings.crawler_request_delay_ms = self.original_delay

    def test_allowed_official_domain_is_fetched(self) -> None:
        transport, _ = make_transport({"https://www.moel.go.kr/faq/faqView.do?seqRepeat=1": HTML})
        page = Fetcher(transport=transport).fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        self.assertEqual(page.content_type, "text/html")

    def test_non_allowlisted_domain_is_refused_without_any_request(self) -> None:
        transport, calls = make_transport({})
        with self.assertRaises(ValueError):
            Fetcher(transport=transport).fetch("https://blog.naver.com/labor-tips")
        self.assertEqual(calls, [])

    def test_http_scheme_is_refused(self) -> None:
        transport, calls = make_transport({})
        with self.assertRaises(ValueError):
            Fetcher(transport=transport).fetch("http://www.moel.go.kr/faq/faqList.do")
        self.assertEqual(calls, [])

    def test_robots_disallow_blocks_the_path(self) -> None:
        robots = (200, "text/plain", b"User-agent: *\nDisallow: /faq/", None)
        transport, calls = make_transport({"https://www.moel.go.kr/robots.txt": robots, "https://www.moel.go.kr/faq/faqView.do?seqRepeat=1": HTML})
        fetcher = Fetcher(transport=transport)
        with self.assertRaises(SkippedURL) as context:
            fetcher.fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        self.assertIn("robots", context.exception.reason)
        self.assertNotIn("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1", calls)

    def test_missing_robots_means_allowed(self) -> None:
        transport, _ = make_transport({"https://www.moel.go.kr/faq/faqView.do?seqRepeat=1": HTML})
        page = Fetcher(transport=transport).fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        self.assertTrue(page.body)

    def test_same_url_is_never_fetched_twice(self) -> None:
        transport, calls = make_transport({"https://www.moel.go.kr/faq/faqView.do?seqRepeat=1": HTML})
        fetcher = Fetcher(transport=transport)
        fetcher.fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        with self.assertRaises(SkippedURL):
            fetcher.fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=1")
        self.assertEqual(len([call for call in calls if "faqView" in call]), 1)

    def test_429_triggers_backoff_then_succeeds(self) -> None:
        responses = [urllib.error.HTTPError("u", 429, "too many", None, None), urllib.error.HTTPError("u", 503, "busy", None, None), HTML]
        transport, calls = make_transport({"https://www.moel.go.kr/faq/faqView.do?seqRepeat=2": responses})
        page = Fetcher(transport=transport).fetch("https://www.moel.go.kr/faq/faqView.do?seqRepeat=2")
        self.assertEqual(page.content_type, "text/html")
        self.assertEqual(len([call for call in calls if "seqRepeat=2" in call]), 3)

    def test_unsupported_content_type_is_skipped(self) -> None:
        transport, _ = make_transport({"https://www.moel.go.kr/a.do?x=1": (200, "application/zip", b"PK", None)})
        with self.assertRaises(SkippedURL):
            Fetcher(transport=transport).fetch("https://www.moel.go.kr/a.do?x=1")

    def test_redirect_to_non_official_domain_is_refused(self) -> None:
        transport, _ = make_transport({"https://www.moel.go.kr/a.do?x=1": (200, "text/html", b"ok", "https://blog.example.com/labor")})
        with self.assertRaises(ValueError):
            Fetcher(transport=transport).fetch("https://www.moel.go.kr/a.do?x=1")


if __name__ == "__main__":
    unittest.main()
