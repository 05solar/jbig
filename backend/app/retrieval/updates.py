# 공식 원문 변경 감지(cron용 fetch·해시 비교·검토 대기 버전 생성)를 담당하는 파일
"""Offline/cron-driven official source change detection for stored RAG documents."""
from __future__ import annotations

import io
import logging
import re
import difflib
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser

from ..core.config import settings
from ..infra.database import list_due_rag_documents, record_rag_check, save_pending_rag_version
from .rag import content_hash, register_document

logger = logging.getLogger(__name__)


class _ReadableHTML(HTMLParser):
    ignored = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript"}

    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in self.ignored:
            self.depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.ignored and self.depth:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.depth:
            self.parts.append(data)


@dataclass(frozen=True)
class FetchResult:
    url: str
    text: str
    content_type: str
    retrieved_at: str


class RedirectLimit(urllib.request.HTTPRedirectHandler):
    def __init__(self, maximum: int):
        super().__init__()
        self.maximum = maximum
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        from .rag import validate_official_url
        validate_official_url(newurl)
        if self.count >= self.maximum:
            raise urllib.error.HTTPError(req.full_url, code, "redirect limit exceeded", headers, None)
        self.count += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _normalize_html(raw: bytes) -> str:
    parser = _ReadableHTML()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def fetch_official_source(url: str) -> FetchResult:
    """Fetch one approved URL with bounded bytes and no automatic redirects."""
    from .rag import validate_official_url
    current = validate_official_url(url)
    opener = urllib.request.build_opener(RedirectLimit(settings.source_max_redirects))
    request = urllib.request.Request(current, headers={"User-Agent": "JB-Bridge-RAG-Checker/1.0", "Accept": "text/html,application/pdf"})
    with opener.open(request, timeout=settings.source_fetch_timeout) as response:
        final_url = response.geturl()
        validate_official_url(final_url)
        content_type = response.headers.get_content_type().lower()
        if content_type not in {"text/html", "application/pdf", "text/plain"}:
            raise ValueError(f"Unsupported source content type: {content_type}")
        body = response.read(settings.source_max_response_bytes + 1)
        if len(body) > settings.source_max_response_bytes:
            raise ValueError("Source response exceeds configured size limit")
    if content_type == "application/pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(body))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            raise ValueError("PDF text extraction failed") from error
    elif content_type == "text/html":
        text = _normalize_html(body)
    else:
        text = body.decode("utf-8", errors="replace")
    if len(text.strip()) < 20:
        raise ValueError("Source content is empty after normalization")
    return FetchResult(url=final_url, text=text, content_type=content_type, retrieved_at=datetime.now(timezone.utc).isoformat())


def next_version(version: str) -> str:
    try:
        return str(int(version) + 1)
    except ValueError:
        return f"{version}-updated"


def summarize_diff(previous: str, current: str, max_lines: int = 30) -> str:
    diff = list(difflib.unified_diff(previous.splitlines(), current.splitlines(), fromfile="previous", tofile="new", lineterm=""))
    return "\n".join(diff[:max_lines]) or "No textual diff available"


def check_source_updates(*, fetcher=fetch_official_source, targets: list[dict[str, str]] | None = None) -> dict[str, int]:
    targets = targets if targets is not None else (list_due_rag_documents() or [])
    summary = {"checked": 0, "unchanged": 0, "changed": 0, "failed": 0, "duplicates": 0}
    if not settings.rag_update_enabled:
        return summary
    for target in targets:
        interval = settings.source_check_interval_law if target.get("document_type") == "law" else settings.source_check_interval_notice if target.get("document_type") in {"notice", "operational", "live"} else settings.source_check_interval_guide
        next_check = (datetime.now(timezone.utc) + timedelta(seconds=interval)).isoformat()
        try:
            fetched = fetcher(target["source_url"])
            summary["checked"] += 1
            digest = content_hash(fetched.text)
            if digest == target["content_hash"]:
                record_rag_check(target["document_id"], next_check_at=next_check)
                summary["unchanged"] += 1
                continue
            pending, chunks = register_document(document_id=target["document_id"], title=target["title"], publisher=target["publisher"], category=target["category"], text=fetched.text, source_url=fetched.url, language=target.get("language", "ko"), verified_at=target.get("verified_at"), version=next_version(target["version"]), active=False, document_type=target.get("document_type", "guide"), effective_from=target.get("effective_from"), status="review_pending", previous_version_id=target.get("version_id") or None)
            if save_pending_rag_version(pending, [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks], diff_summary=summarize_diff(target.get("content", ""), fetched.text)):
                summary["changed"] += 1
            else:
                summary["duplicates"] += 1
            record_rag_check(target["document_id"], next_check_at=next_check)
        except Exception as error:
            summary["failed"] += 1
            record_rag_check(target["document_id"], next_check_at=next_check, error=type(error).__name__ + ": " + str(error))
            logger.warning("RAG source check failed document_id=%s error=%s", target.get("document_id"), type(error).__name__)
    return summary
