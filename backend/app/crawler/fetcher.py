# 공식 도메인 전용 수집기(robots.txt 준수·요청 간격·지수 백오프·중복 요청 금지)를 담당하는 파일
"""Polite HTTP fetcher for official sites only.

Every URL is validated against the RAG domain allowlist before any request,
robots.txt is honoured per host, requests to the same host are spaced by
CRAWLER_REQUEST_DELAY_MS, 429/503 responses trigger exponential backoff, and a
URL is never fetched twice in one run."""
from __future__ import annotations

import logging
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from urllib.parse import urlparse

from ..core.config import settings
from ..retrieval.rag import validate_official_url
from ..retrieval.updates import RedirectLimit

logger = logging.getLogger(__name__)

FETCHABLE_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "application/pdf", "text/plain"}


class SkippedURL(Exception):
    """Raised when a URL must not be fetched (robots, revisit, disallowed type)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class FetchedPage:
    url: str
    final_url: str
    content_type: str
    body: bytes


def _default_transport(url: str) -> tuple[int, str, bytes, str]:
    opener = urllib.request.build_opener(RedirectLimit(settings.source_max_redirects))
    request = urllib.request.Request(url, headers={"User-Agent": settings.crawler_user_agent, "Accept": "text/html,application/xhtml+xml,application/pdf,text/plain"})
    with opener.open(request, timeout=settings.crawler_timeout_seconds) as response:
        body = response.read(settings.source_max_response_bytes + 1)
        if len(body) > settings.source_max_response_bytes:
            raise ValueError("Response exceeds configured size limit")
        return getattr(response, "status", 200) or 200, response.headers.get_content_type().lower(), body, response.geturl()


class Fetcher:
    """One instance per crawl run. transport is injectable so tests stay offline."""

    def __init__(self, *, transport=None):
        self._transport = transport or _default_transport
        self._visited: set[str] = set()
        self._last_request: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._lock = threading.Lock()

    def _robots_for(self, host: str) -> urllib.robotparser.RobotFileParser | None:
        if host in self._robots:
            return self._robots[host]
        parser = urllib.robotparser.RobotFileParser()
        try:
            status, content_type, body, _ = self._transport(f"https://{host}/robots.txt")
            if status == 200 and content_type.startswith("text"):
                parser.parse(body.decode("utf-8", errors="replace").splitlines())
            else:
                parser = None
        except Exception:
            # Missing/broken robots.txt means no stated restriction (standard behaviour).
            parser = None
        self._robots[host] = parser
        return parser

    def robots_allows(self, url: str) -> bool:
        if not settings.crawler_respect_robots:
            return True
        host = (urlparse(url).hostname or "").lower()
        parser = self._robots_for(host)
        return True if parser is None else parser.can_fetch(settings.crawler_user_agent, url)

    def _throttle(self, host: str) -> None:
        delay = settings.crawler_request_delay_ms / 1000.0
        while True:
            with self._lock:
                now = time.monotonic()
                ready = self._last_request.get(host, 0.0) + delay
                if now >= ready:
                    self._last_request[host] = now
                    return
                wait = ready - now
            time.sleep(wait)

    def fetch(self, url: str) -> FetchedPage:
        """Fetch one allowlisted URL politely. Raises SkippedURL/ValueError on refusal."""
        current = validate_official_url(url)
        host = (urlparse(current).hostname or "").lower()
        with self._lock:
            if current in self._visited:
                raise SkippedURL("already visited in this run")
            self._visited.add(current)
        if not self.robots_allows(current):
            raise SkippedURL("blocked by robots.txt")
        attempts = 0
        while True:
            self._throttle(host)
            try:
                status, content_type, body, final_url = self._transport(current)
            except urllib.error.HTTPError as error:
                if error.code in (429, 503) and attempts < settings.crawler_max_retries:
                    backoff = (settings.crawler_request_delay_ms / 1000.0) * (2 ** attempts)
                    logger.info("HTTP %s from %s; backing off %.1fs", error.code, host, backoff)
                    time.sleep(backoff)
                    attempts += 1
                    continue
                raise
            validate_official_url(final_url)
            if status != 200:
                raise ValueError(f"HTTP {status}")
            if content_type not in FETCHABLE_CONTENT_TYPES:
                raise SkippedURL(f"unsupported content type: {content_type}")
            return FetchedPage(url=current, final_url=final_url, content_type=content_type, body=body)
