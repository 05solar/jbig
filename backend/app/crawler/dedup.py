# 중복 제거(정규화 URL·제목 정규화·본문 해시·유사 본문 감지)를 담당하는 파일
"""Duplicate detection for crawled candidates.

Order of checks: canonical URL -> exact content fingerprint -> normalized
title + near-identical token set. URL-parameter-only variants of the same page
collapse to one candidate."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..retrieval.rag import content_hash

TRACKING_PARAMS = ("utm_", "ga_", "fbclid", "gclid", "ref", "referer", "token", "sid", "s_id", "menuno_top")


def canonical_url(url: str) -> str:
    """Stable identity for a page: drop session ids, tracking params, fragments; sort query."""
    parsed = urlparse(url)
    path = re.sub(r";jsessionid=[^/?#]*", "", parsed.path, flags=re.IGNORECASE)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    params = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=False)
              if not any(key.lower().startswith(prefix) for prefix in TRACKING_PARAMS) and key.lower() != "jsessionid"]
    params.sort()
    return urlunparse((parsed.scheme.lower(), (parsed.netloc or "").lower(), path, "", urlencode(params), ""))


def normalize_title(title: str) -> str:
    return re.sub(r"[\s\W_]+", "", title).lower()


def content_fingerprint(body: str) -> str:
    """Whitespace-insensitive body hash so re-rendered pages still match."""
    return content_hash(re.sub(r"\s+", "", body))


def _token_set(body: str) -> frozenset[str]:
    return frozenset(re.findall(r"[가-힣a-zA-Z0-9]{2,}", body.lower()))


class DedupRegistry:
    """Per-run duplicate registry; check() returns None or a rejection reason."""

    def __init__(self, near_duplicate_threshold: float = 0.9):
        self.threshold = near_duplicate_threshold
        self._urls: set[str] = set()
        self._fingerprints: set[str] = set()
        self._titles: dict[str, frozenset[str]] = {}

    def check(self, canonical: str, title: str, body: str) -> str | None:
        if canonical in self._urls:
            return "duplicate_url"
        fingerprint = content_fingerprint(body)
        if fingerprint in self._fingerprints:
            return "duplicate_content"
        title_key = normalize_title(title)
        tokens = _token_set(body)
        if title_key and title_key in self._titles:
            known = self._titles[title_key]
            union = len(known | tokens)
            if union and len(known & tokens) / union >= self.threshold:
                return "duplicate_content"
        self._urls.add(canonical)
        self._fingerprints.add(fingerprint)
        if title_key:
            self._titles.setdefault(title_key, tokens)
        return None
