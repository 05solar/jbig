# 수집 파이프라인(목록→상세 수집·정제·중복제거·review_pending 등록·보고서)을 담당하는 파일
"""Crawl orchestration: list pages -> detail pages -> filters -> review_pending.

Hard rules enforced here (§15, §31):
- crawled documents are NEVER written as active; new documents get
  status=review_pending / active=false, changed documents become a pending
  version while the existing active version keeps serving
- only specific detail URLs are stored as source_url
- no OpenAI/LLM/embedding call happens anywhere in this package; embeddings are
  produced only after an administrator approves a version"""
from __future__ import annotations

import hashlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from ..core.config import settings
from ..retrieval.rag import content_hash, is_specific_source_url, register_document
from .base import CrawlCandidate, CrawlReport, SourceSpec
from .dedup import DedupRegistry, canonical_url
from .fetcher import Fetcher, SkippedURL
from .filters import is_allowed_detail_url, is_irrelevant, quality_score
from .parser import decode_body, detect_language, extract_pdf_text, extract_published_at, parse_page

logger = logging.getLogger(__name__)


def document_id_for(spec: SourceSpec, canonical: str) -> str:
    """Deterministic id per canonical URL so re-crawls map to the same document."""
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:10]
    return f"crawl-{spec.key}-{digest}"


def collect_detail_urls(spec: SourceSpec, fetcher: Fetcher, report: CrawlReport, limit: int) -> list[str]:
    """Fetch the spec's list pages and return unique allowed detail URLs (list->detail only, no BFS)."""
    found: list[str] = []
    seen: set[str] = set()

    def add(url: str, *, direct: bool = False) -> None:
        canonical = canonical_url(url)
        if canonical in seen:
            return
        if direct:
            # Direct content pages skip the detail-link pattern but still must be
            # on-domain, specific (not a homepage root) and not on a denied path.
            from urllib.parse import urlparse
            from .filters import is_denied_url
            host = (urlparse(canonical).hostname or "").lower()
            if host != spec.domain.lower() or is_denied_url(canonical) or not is_specific_source_url(canonical):
                return
        elif not is_allowed_detail_url(canonical, spec):
            return
        seen.add(canonical)
        found.append(canonical)

    for url in spec.direct_pages:
        add(url, direct=True)
    for list_url in spec.list_urls:
        if len(found) >= limit:
            break
        try:
            page = fetcher.fetch(list_url)
        except SkippedURL as skip:
            if "robots" in skip.reason:
                report.bump(spec.domain, "robots_blocked")
            continue
        except Exception as error:
            report.errors.append(f"{list_url}: {type(error).__name__}: {error}")
            continue
        report.bump(spec.domain, "visited_urls")
        html = decode_body(page.body)
        parsed = parse_page(html, page.final_url)
        for href, _text in parsed.links:
            add(href)
        if spec.onclick_pattern and spec.onclick_template:
            for identifier in re.findall(spec.onclick_pattern, html):
                add(spec.onclick_template.format(id=identifier))
    return found[:limit]


def build_candidate(spec: SourceSpec, url: str, fetcher: Fetcher, report: CrawlReport, dedup: DedupRegistry, since: str | None) -> CrawlCandidate | None:
    """Fetch and validate one detail page; returns None when rejected (reason is counted)."""
    try:
        page = fetcher.fetch(url)
    except SkippedURL as skip:
        if "robots" in skip.reason:
            report.bump(spec.domain, "robots_blocked")
        return None
    except Exception as error:
        report.errors.append(f"{url}: {type(error).__name__}: {error}")
        return None
    report.bump(spec.domain, "visited_urls")
    report.bump(spec.domain, "detail_pages")
    final_canonical = canonical_url(page.final_url)
    if not is_specific_source_url(final_canonical):
        report.bump(spec.domain, "generic_urls")
        return None
    if page.content_type == "application/pdf":
        try:
            body = extract_pdf_text(page.body)
        except Exception as error:
            report.errors.append(f"{url}: PDF extraction failed: {type(error).__name__}")
            return None
        title = body.strip().splitlines()[0][:120] if body.strip() else ""
        published_at = extract_published_at(body[:4000])
    else:
        parsed = parse_page(decode_body(page.body), page.final_url)
        body, title, published_at = parsed.body, parsed.title, parsed.published_at
    body = body.strip()
    if len(body) < settings.crawler_min_content_chars:
        report.bump(spec.domain, "rejected_short")
        return None
    if is_irrelevant(title, body, spec.category):
        report.bump(spec.domain, "rejected_irrelevant")
        return None
    if since and published_at and published_at < since:
        report.bump(spec.domain, "rejected_irrelevant")
        return None
    reason = dedup.check(final_canonical, title, body)
    if reason:
        report.bump(spec.domain, "rejected_duplicate")
        return None
    candidate = CrawlCandidate(spec=spec, url=page.final_url, canonical_url=final_canonical, title=title, body=body, published_at=published_at, language=detect_language(body), content_type=page.content_type)
    candidate.quality = quality_score(candidate)
    report.bump(spec.domain, "accepted_candidates")
    return candidate


def register_candidates(candidates: list[CrawlCandidate], report: CrawlReport) -> None:
    """Persist candidates as review_pending only (never active). §14/§15."""
    from ..infra.database import get_rag_document_summary, record_rag_check, save_crawled_document_pending, save_pending_rag_version
    from ..retrieval.updates import next_version

    for candidate in candidates:
        spec = candidate.spec
        document_id = document_id_for(spec, candidate.canonical_url)
        try:
            current = get_rag_document_summary(document_id)
            version = next_version(current["version"]) if current else "1"
            document, chunks = register_document(
                document_id=document_id, title=candidate.title, publisher=spec.publisher, category=spec.category,
                text=candidate.body, source_url=candidate.canonical_url, language=candidate.language,
                published_at=candidate.published_at, version=version, active=False,
                document_type=spec.document_type, status="review_pending",
                previous_version_id=(current or {}).get("version_id") or None,
            )
            chunk_rows = [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks]
            if current and current["content_hash"] == document.content_hash:
                interval = settings.source_check_interval_guide
                record_rag_check(document_id, next_check_at=(datetime.now(timezone.utc) + timedelta(seconds=interval)).isoformat())
                report.bump(spec.domain, "unchanged_documents")
            elif current:
                if save_pending_rag_version(document, chunk_rows, quality_score=candidate.quality):
                    report.bump(spec.domain, "updated_documents")
                else:
                    report.bump(spec.domain, "rejected_duplicate")
            else:
                if save_crawled_document_pending(document, chunk_rows, quality_score=candidate.quality):
                    report.bump(spec.domain, "new_documents")
                else:
                    report.bump(spec.domain, "rejected_duplicate")
        except Exception as error:
            report.errors.append(f"{candidate.canonical_url}: register failed: {type(error).__name__}: {error}")


def run_crawl(specs: tuple[SourceSpec, ...], *, limit: int | None = None, dry_run: bool = False, since: str | None = None, fetcher: Fetcher | None = None) -> tuple[CrawlReport, list[CrawlCandidate]]:
    """Crawl the given source specs and (unless dry_run) register review_pending documents."""
    report = CrawlReport()
    if not settings.crawler_enabled:
        report.errors.append("crawler is disabled (CRAWLER_ENABLED=false)")
        return report, []
    fetcher = fetcher or Fetcher()
    per_source_limit = limit or settings.crawler_max_detail_pages
    all_candidates: list[CrawlCandidate] = []

    def crawl_source(spec: SourceSpec) -> list[CrawlCandidate]:
        dedup = DedupRegistry()
        candidates: list[CrawlCandidate] = []
        for url in collect_detail_urls(spec, fetcher, report, per_source_limit):
            candidate = build_candidate(spec, url, fetcher, report, dedup, since)
            if candidate:
                candidates.append(candidate)
        return candidates

    workers = max(1, min(settings.crawler_max_concurrency, len(specs) or 1))
    if workers == 1 or len(specs) <= 1:
        for spec in specs:
            all_candidates.extend(crawl_source(spec))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for result in pool.map(crawl_source, specs):
                all_candidates.extend(result)
    all_candidates.sort(key=lambda candidate: -candidate.quality)
    if not dry_run:
        register_candidates(all_candidates, report)
    return report, all_candidates
