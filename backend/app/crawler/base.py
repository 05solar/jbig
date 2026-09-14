# 크롤러 공용 자료구조(수집 대상 정의·후보 문서·실행 보고서)를 정의하는 파일
"""Shared crawler data structures. No network access in this module."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.schemas import Category


@dataclass(frozen=True)
class SourceSpec:
    """One official site section: list pages that link to detail documents.

    detail_patterns are regexes matched against resolved hrefs; onclick_pattern
    extracts JS-only detail ids (gov boards often use fn_select('id')) which are
    expanded through onclick_template. direct_pages are content pages that are
    themselves the document (no list->detail hop)."""

    key: str
    domain: str
    publisher: str
    category: Category
    document_type: str = "guide"
    language: str = "ko"
    list_urls: tuple[str, ...] = ()
    detail_patterns: tuple[str, ...] = ()
    onclick_pattern: str | None = None
    onclick_template: str | None = None
    direct_pages: tuple[str, ...] = ()


@dataclass
class CrawlCandidate:
    """A parsed detail page that passed extraction (filters may still reject it)."""

    spec: SourceSpec
    url: str
    canonical_url: str
    title: str
    body: str
    published_at: str | None = None
    language: str = "ko"
    content_type: str = "text/html"
    quality: float = 0.0


@dataclass
class CrawlReport:
    """Counters for one crawl run; per_domain mirrors the totals per host."""

    visited_urls: int = 0
    detail_pages: int = 0
    accepted_candidates: int = 0
    rejected_irrelevant: int = 0
    rejected_short: int = 0
    rejected_duplicate: int = 0
    generic_urls: int = 0
    robots_blocked: int = 0
    new_documents: int = 0
    updated_documents: int = 0
    unchanged_documents: int = 0
    errors: list[str] = field(default_factory=list)
    per_domain: dict[str, dict[str, int]] = field(default_factory=dict)

    def bump(self, domain: str, counter: str, amount: int = 1) -> None:
        setattr(self, counter, getattr(self, counter) + amount)
        bucket = self.per_domain.setdefault(domain, {})
        bucket[counter] = bucket.get(counter, 0) + amount

    def as_dict(self) -> dict:
        return {
            "visited_urls": self.visited_urls, "detail_pages": self.detail_pages,
            "accepted_candidates": self.accepted_candidates, "rejected_irrelevant": self.rejected_irrelevant,
            "rejected_short": self.rejected_short, "rejected_duplicate": self.rejected_duplicate,
            "generic_urls": self.generic_urls, "robots_blocked": self.robots_blocked,
            "new_documents": self.new_documents, "updated_documents": self.updated_documents,
            "unchanged_documents": self.unchanged_documents, "errors": self.errors, "per_domain": self.per_domain,
        }
