# 수집 후보 필터(허용/제외 URL 패턴·관련성 키워드·무관 페이지 차단·품질 점수)를 담당하는 파일
"""Deterministic relevance/quality filters for crawled pages. No LLM calls.

quality score is used only to sort the admin review queue — never for
auto-approval."""
from __future__ import annotations

import re
from urllib.parse import urlparse

from ..core.config import settings
from ..retrieval.rag import is_specific_source_url
from .base import CrawlCandidate, SourceSpec

DENY_URL_HINTS = ("/recruit", "/organization", "/photo", "/gallery", "/event", "/press", "/news", "/login", "/member", "/search", "/eng/", "/kids", "greeting", "sitemap", "privacy", "copyright")
DENY_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".zip", ".exe", ".xls", ".xlsx", ".ppt", ".pptx", ".mp4", ".css", ".js")

RELEVANCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "residency": ("외국인", "체류", "비자", "등록증", "출입국", "입국", "출국", "재입국", "영주", "귀화", "국적", "통합신청", "하이코리아", "사증", "residence", "visa", "immigration", "alien", "foreigner", "다문화", "민원", "정부24", "건강보험", "혼인", "가족", "정착", "상담센터", "지원센터", "외국인등록"),
    "labor": ("임금", "근로", "노동", "고용", "해고", "연차", "휴가", "휴일", "휴게", "수당", "퇴직", "산재", "산업재해", "최저임금", "근로계약", "임금명세", "체불", "괴롭힘", "고용허가", "외국인근로자", "사업장", "위약금", "숙식비", "wage", "labor", "employment", "dismissal", "severance"),
}

IRRELEVANT_TITLE_MARKERS = ("채용", "모집공고", "입찰", "낙찰", "인사말", "조직도", "오시는 길", "찾아오시는", "포토", "갤러리", "동정", "행사안내", "공모전", "시무식", "간담회", "워크숍", "기관장", "임명", "수상", "협약식", "발대식")


def is_denied_url(url: str) -> bool:
    lowered = url.lower()
    return any(hint in lowered for hint in DENY_URL_HINTS) or lowered.split("?")[0].endswith(DENY_EXTENSIONS)


def is_allowed_detail_url(url: str, spec: SourceSpec) -> bool:
    """Detail URL: on the spec's domain, matches a detail pattern, not denied, not a homepage root."""
    host = (urlparse(url).hostname or "").lower()
    if host != spec.domain.lower() or is_denied_url(url):
        return False
    if not is_specific_source_url(url):
        return False
    return any(re.search(pattern, url) for pattern in spec.detail_patterns)


def relevance_hits(title: str, body: str, category: str) -> int:
    keywords = RELEVANCE_KEYWORDS.get(category, ())
    haystack = f"{title}\n{body[:2000]}".lower()
    return sum(1 for keyword in keywords if keyword.lower() in haystack)


def is_irrelevant(title: str, body: str, category: str) -> bool:
    if any(marker in title for marker in IRRELEVANT_TITLE_MARKERS):
        return True
    return relevance_hits(title, body, category) == 0


def looks_like_menu_text(body: str) -> bool:
    """Menu dumps are many very short lines; articles have sentence-length lines."""
    lines = [line for line in body.splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    short = sum(1 for line in lines if len(line.strip()) <= 12)
    return short / len(lines) > 0.8


def quality_score(candidate: CrawlCandidate) -> float:
    """0..1 review-priority score (§12). Never used for auto-approval."""
    score = 0.0
    if is_specific_source_url(candidate.canonical_url):
        score += 0.25
    body_length = len(candidate.body)
    if body_length >= settings.crawler_min_content_chars:
        score += 0.2
    if body_length >= 1000:
        score += 0.05
    title = candidate.title.strip()
    if 6 <= len(title) <= 120 and not any(marker in title for marker in IRRELEVANT_TITLE_MARKERS):
        score += 0.15
    hits = relevance_hits(candidate.title, candidate.body, candidate.spec.category)
    score += min(0.2, 0.05 * hits)
    if candidate.spec.publisher:
        score += 0.1
    if candidate.published_at:
        score += 0.05
    if looks_like_menu_text(candidate.body):
        score -= 0.2
    return round(max(0.0, min(1.0, score)), 2)
