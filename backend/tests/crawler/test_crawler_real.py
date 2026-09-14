# 실제 공식 사이트 소수 페이지 실크롤링 검증(RAG_CRAWLER_REAL_TEST=1일 때만 실행)을 담당하는 테스트 파일
"""Live-site smoke tests. Disabled by default so external outages never break CI.

Enable with: RAG_CRAWLER_REAL_TEST=1"""
import os
import unittest

from app.core.config import settings
from app.crawler import sources_for
from app.crawler.pipeline import run_crawl

REAL_ENABLED = os.environ.get("RAG_CRAWLER_REAL_TEST") == "1"


@unittest.skipUnless(REAL_ENABLED, "set RAG_CRAWLER_REAL_TEST=1 to hit real official sites")
class RealCrawlSmokeTests(unittest.TestCase):
    """Fetches at most a couple of detail pages per domain (dry-run, no DB writes)."""

    def crawl_domain(self, domain: str, limit: int = 3):
        specs = sources_for(domain)
        self.assertTrue(specs, f"no source spec for {domain}")
        report, candidates = run_crawl(specs, limit=limit, dry_run=True)
        return report, candidates

    def assert_candidates_valid(self, candidates) -> None:
        for candidate in candidates:
            self.assertTrue(candidate.title)
            self.assertGreaterEqual(len(candidate.body), settings.crawler_min_content_chars)
            self.assertIn(candidate.spec.domain, candidate.canonical_url)
            self.assertTrue(candidate.canonical_url.startswith("https://"))
            self.assertNotEqual(candidate.canonical_url.rstrip("/"), f"https://{candidate.spec.domain}")

    def test_moel_faq_detail_pages(self) -> None:
        report, candidates = self.crawl_domain("moel.go.kr")
        self.assertGreaterEqual(len(candidates), 1, f"no candidates; report={report.as_dict()}")
        self.assert_candidates_valid(candidates)

    def test_minimumwage_pages(self) -> None:
        report, candidates = self.crawl_domain("minimumwage.go.kr")
        self.assertGreaterEqual(len(candidates), 1, f"no candidates; report={report.as_dict()}")
        self.assert_candidates_valid(candidates)


if __name__ == "__main__":
    unittest.main()
