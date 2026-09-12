"""Reviewed official-document RAG primitives.

This module deliberately accepts text and metadata rather than fetching URLs. A
separate administrator/import job can call register_document() after review.
"""
from __future__ import annotations

import hashlib
import ipaddress
import re
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from .config import settings
from .schemas import Category, RAGDocument, RAGSource


@dataclass(frozen=True)
class OfficialChunk:
    document: RAGDocument
    chunk_id: str
    text: str
    chunk_index: int


def allowed_domains() -> set[str]:
    return {item.strip().lower() for item in settings.rag_allowed_domains.split(",") if item.strip()}


def validate_official_url(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme != "https" or not host or not any(host == domain or host.endswith(f".{domain}") for domain in allowed_domains()):
        raise ValueError("URL is not on the approved official HTTPS domain list")
    try:
        address = ipaddress.ip_address(host)
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
            raise ValueError("Private or local URL is not allowed")
    except ValueError as error:
        if "not allowed" in str(error):
            raise
        try:
            for resolved in socket.getaddrinfo(host, None):
                address = ipaddress.ip_address(resolved[4][0])
                if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved:
                    raise ValueError("URL resolves to a private or local address")
        except socket.gaierror:
            # Registration can occur offline; DNS is checked again by a fetcher.
            pass
    return url


def normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def redact_for_embedding(text: str) -> str:
    """Keep reviewed source text intact in storage but avoid embedding identifiers."""
    text = re.sub(r"(?<!\d)\d{6}[- ]?\d{6,7}(?!\d)", "[REDACTED-ID]", text)
    text = re.sub(r"(?<!\d)(01[016789][- ]?\d{3,4}[- ]?\d{4})(?!\d)", "[REDACTED-PHONE]", text)
    return text


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def split_chunks(text: str, chunk_size: int = 900, overlap: int = 120) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(len(normalized), start + chunk_size)
        if end < len(normalized):
            boundary = max(normalized.rfind("\n", start, end), normalized.rfind(".", start, end), normalized.rfind(".", start, end))
            if boundary > start + chunk_size // 2:
                end = boundary + 1
        chunks.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(start + 1, end - overlap)
    return chunks


def register_document(*, document_id: str, title: str, publisher: str, category: Category, text: str, source_url: str, language: str = "ko", issued_at: str | None = None, verified_at: str | None = None, version: str = "1", active: bool = True, document_type: str | None = None, published_at: str | None = None, promulgated_at: str | None = None, effective_from: str | None = None, effective_until: str | None = None, status: str | None = None, previous_version_id: str | None = None) -> tuple[RAGDocument, list[OfficialChunk]]:
    validate_official_url(source_url)
    normalized = normalize_text(text)
    if not normalized:
        raise ValueError("Document text cannot be empty")
    now = datetime.now(timezone.utc)
    digest = content_hash(normalized)
    doc_type = document_type or ("law" if "법" in title or "고시" in title else "guide")
    interval = settings.source_check_interval_law if doc_type == "law" else settings.source_check_interval_notice if doc_type in {"notice", "operational", "live"} else settings.source_check_interval_guide
    document = RAGDocument(document_id=document_id, title=title, publisher=publisher, source_organization=publisher, source_domain=(urlparse(source_url).hostname or "").lower(), document_type=doc_type, category=category, original_text=normalized, source_url=source_url, language=language, issued_at=issued_at, published_at=published_at, promulgated_at=promulgated_at, effective_from=effective_from, effective_until=effective_until, collected_at=date.today().isoformat(), retrieved_at=now.isoformat(), last_checked_at=now.isoformat(), next_check_at=(now + timedelta(seconds=interval)).isoformat(), verified_at=verified_at or date.today().isoformat(), version=version, version_id=f"{document_id}:{version}:{digest[:12]}", content_hash=digest, active=active, status=status or ("active" if active else "inactive"), previous_version_id=previous_version_id, index_version=settings.rag_index_version)
    chunks = [OfficialChunk(document, f"{document_id}:{index}", chunk, index) for index, chunk in enumerate(split_chunks(normalized))]
    return document, chunks


SAMPLE_DOCUMENTS = (
    register_document(document_id="hikorea-stay-extension-status", title="하이코리아 체류기간 연장 신청 확인", publisher="하이코리아", category="residency", source_url="https://www.hikorea.go.kr/", text="체류기간 연장 신청 전에는 체류 만료일과 신청 가능한 방법을 확인합니다. 신청 진행상태와 처리 결과는 하이코리아 전자민원 또는 관할 출입국기관, 1345를 통해 본인 인증 후 확인합니다. 처리 중인 신청의 허가 여부를 AI가 확정할 수 없으므로 공식 채널의 최신 상태를 확인해야 합니다."),
    register_document(document_id="immigration-residence-card-correction", title="체류민원 자주 묻는 질문: 외국인등록증 정정", publisher="법무부 출입국·외국인정책본부", category="residency", source_url="https://www.immigration.go.kr/", text="외국인등록증의 영문 이름이나 인적사항이 여권과 다르면 관할 출입국·외국인관서에 정정 가능 여부와 필요한 증빙서류를 문의해야 합니다. 여권 원본과 등록증, 변경 사실을 확인할 수 있는 자료를 준비합니다. 개별 체류자격과 사실관계에 따라 요구서류와 처리방법이 달라질 수 있으므로 하이코리아 또는 1345에서 확인합니다."),
    register_document(document_id="hikorea-student-part-time-work", title="유학생 시간제취업(아르바이트) 안내", publisher="하이코리아", category="residency", source_url="https://www.hikorea.go.kr/", text="유학생이 시간제취업을 하려면 체류자격별 허용 여부, 근무시간과 장소, 필요한 사전 허가 또는 신고 절차를 시작 전에 확인해야 합니다. 여권, 외국인등록증, 재학 및 성적 관련 서류, 근로계약서 등 제출서류는 개인의 체류자격과 학교 상황에 따라 달라질 수 있습니다. 허가 전 근무 가능 여부는 1345와 관할 출입국기관에 확인합니다."),
    register_document(document_id="moel-employment-contract-working-hours", title="근로계약서와 실제 근로시간이 다른 경우", publisher="고용노동부", category="labor", source_url="https://www.moel.go.kr/policy/policybbs/workinghour/detailList.do?tpi_seq=20", text="근로계약서의 근무시간과 실제 근무시간이 다르면 출퇴근기록, 근무표, 업무지시, 급여명세서와 메시지를 보관하고 사업주에게 사실관계 확인을 요청합니다. 임금 또는 근로시간 문제가 해결되지 않으면 고용노동부 상담전화 1350이나 관할 노동관서에 상담과 신고 방법을 문의합니다. 구체적인 위반 여부와 받을 수 있는 금액은 자료 확인이 필요합니다."),
    register_document(document_id="moel-written-employment-contract", title="근로조건의 서면 명시와 근로계약서 교부", publisher="고용노동부", category="labor", source_url="https://1350.moel.go.kr/rtmview.do?id=1000302992", text="사용자는 근로계약을 체결할 때 임금, 소정근로시간, 휴일 등 주요 근로조건을 서면으로 명시하고 근로자에게 교부해야 합니다. 근로계약서가 없거나 실제 근로조건과 서면 내용이 다르면 계약서, 급여명세서, 출퇴근기록과 메시지를 보관하고 관할 노동관서 또는 1350에 상담하세요. 구체적인 위반 여부와 구제 방법은 사업장과 사실관계 확인이 필요합니다."),
    register_document(document_id="moel-wage-deduction-housing", title="임금에서 공제되는 숙소비 확인", publisher="고용노동부", category="labor", source_url="https://1350.moel.go.kr/rtmview.do?id=1000028169&page=11601&type=ALL", text="사업주가 숙소비를 임금에서 공제했다면 근로계약서, 급여명세서, 공제 동의나 안내 자료, 실제 지급 내역을 비교합니다. 공제 항목과 금액의 근거가 불명확하면 사업주에게 서면 설명을 요청하고 고용노동부 1350에 상담합니다. 공제의 적법성은 계약 내용과 관련 법령, 실제 지급 자료에 따라 판단되므로 AI가 확정하지 않습니다."),
    register_document(document_id="moel-unpaid-dismissal-together", title="임금체불과 해고 문제가 함께 발생한 경우", publisher="고용노동부", category="labor", source_url="https://1350.moel.go.kr/rtmview.do?id=1000307546", text="임금체불과 해고가 동시에 발생했다면 근로계약서, 급여명세서, 계좌내역, 출퇴근기록, 해고 통지와 메시지를 함께 보관합니다. 임금 문제는 고용노동부 1350, 해고 구제 절차는 관할 노동위원회에 상담하고 각 신청의 요건과 기간을 확인합니다. 구체적인 위반 여부나 구제 가능성은 자료와 사실관계에 따라 달라집니다."),
)


def _tokens(text: str) -> set[str]:
    normalized = text.casefold()
    aliases = {
        "영문 이름": "이름 정정", "english name": "이름 정정", "student": "유학생",
        "part-time": "시간제취업", "아르바이트": "시간제취업", "음식점": "시간제취업",
        "유학": "유학생", "d-2": "유학생", "working hours": "근로시간", "hours": "근로시간",
        "하루 8시간": "근로시간", "11시간씩": "근로시간", "근로계약서에는": "근로계약서",
        "근로계약서는": "근로계약서", "근로계약서의": "근로계약서", "근무시간과": "근로시간",
        "근로시간이": "근로시간", "숙소비": "공제", "housing fee": "숙소비",
        "wage deduction": "공제", "임금을": "임금", "임금은": "임금", "돈을 안줘요": "임금",
        "돈을 안줘": "임금", "돈을 못": "임금", "부당해고": "해고", "체류기간 연장": "체류연장",
        "체류기간": "체류", "fired": "해고", "dismissal": "해고", "lương": "임금",
        "sinh viên": "유학생", "làm thêm": "시간제취업"
    }
    for source, target in aliases.items():
        normalized = normalized.replace(source, f" {target} ")
    stopwords = {"있습니다", "합니다", "경우", "확인", "관련", "대한", "통해", "자료", "내용", "수", "다를", "다르면", "따라", "것", "있는", "하는", "어떻게", "해야", "하나요"}
    tokens = {token for token in re.findall(r"[a-z0-9가-힣]{2,}", normalized) if token not in stopwords}
    # Preserve useful Korean compound prefixes for matching a question such as
    # "임금을" with a reviewed source titled "임금체불".
    for compound, prefix in (("임금체불", "임금"), ("부당해고", "해고"), ("근무시간", "근무"), ("근로계약서", "근로계약서"), ("외국인등록증", "등록증"), ("체류기간", "체류")):
        if compound in normalized:
            tokens.add(prefix)
    return tokens


def _sample_chunks() -> list[OfficialChunk]:
    return [chunk for _, chunks in SAMPLE_DOCUMENTS for chunk in chunks]


def search_official_documents(question: str, *, category: Category | None = None, limit: int | None = None, chunks: list[OfficialChunk] | None = None) -> list[tuple[OfficialChunk, float]]:
    """Deterministic lexical baseline; DB/vector results can be passed in or layered by the caller."""
    query = _tokens(question)
    if not query:
        return []
    candidates = chunks if chunks is not None else _sample_chunks()
    scored: list[tuple[OfficialChunk, float]] = []
    for chunk in candidates:
        if not chunk.document.active or category and chunk.document.category != category:
            continue
        try:
            today = date.today()
            if chunk.document.effective_from and date.fromisoformat(chunk.document.effective_from) > today:
                continue
            if chunk.document.effective_until and date.fromisoformat(chunk.document.effective_until) < today:
                continue
        except ValueError:
            continue
        if chunk.document.status not in {"active", "approved", "fetch_failed"}:
            continue
        title_tokens = _tokens(chunk.document.title)
        tokens = _tokens(f"{chunk.document.title} {chunk.document.publisher} {chunk.text}")
        overlap = len(query & tokens)
        if overlap == 0:
            continue
        # A long compound question may contribute only one distinctive term to
        # each relevant document, so do not dilute that evidence excessively.
        title_overlap = len(query & title_tokens)
        score = min(0.99, 0.22 + overlap / max(4, len(query)) * 0.78 + min(0.12, title_overlap * 0.06))
        scored.append((chunk, round(score, 3)))
    scored.sort(key=lambda item: item[1], reverse=True)
    threshold = settings.rag_similarity_threshold
    return [(chunk, score) for chunk, score in scored if score >= threshold][: limit or settings.rag_top_k]


def indexed_chunks() -> list[OfficialChunk]:
    try:
        from .database import load_rag_chunks
        stored = load_rag_chunks()
        if stored:
            return [OfficialChunk(document, chunk_id, text, index) for document, chunk_id, text, index in stored]
    except Exception:
        pass
    return _sample_chunks()


def search_index(question: str, *, category: Category | None = None, limit: int | None = None) -> list[tuple[OfficialChunk, float]]:
    lexical = search_official_documents(question, category=category, limit=limit, chunks=indexed_chunks())
    if settings.openai_api_key:
        try:
            from .embeddings import create_embeddings
            from .database import search_rag_vectors
            vector_matches = search_rag_vectors(create_embeddings([normalize_text(question)])[0], limit or settings.rag_top_k, settings.rag_similarity_threshold)
            if vector_matches:
                vector_chunks = [(OfficialChunk(document, chunk_id, text, index), score) for document, chunk_id, text, index, score in vector_matches if category is None or document.category == category]
                merged = {chunk.chunk_id: (chunk, score) for chunk, score in lexical}
                for chunk, score in vector_chunks:
                    merged[chunk.chunk_id] = (chunk, max(score, merged.get(chunk.chunk_id, (chunk, 0))[1]))
                return sorted(merged.values(), key=lambda item: item[1], reverse=True)[: limit or settings.rag_top_k]
        except Exception:
            pass
    return lexical


def source_from_chunk(chunk: OfficialChunk, relevance: float) -> RAGSource:
    document = chunk.document
    freshness = "live_verification_required" if document.document_type in {"operational", "live"} else "versioned"
    status = "최신성 재확인 필요" if document.status == "fetch_failed" or (document.next_check_at and document.next_check_at < datetime.now(timezone.utc).isoformat()) else "최신 공식자료 확인 완료"
    authority_score, trust_level, reasons = trust_for_document(document, status)
    return RAGSource(document_id=document.document_id, chunk_id=chunk.chunk_id, title=document.title, publisher=document.source_organization or document.publisher, url=document.source_url, verified_at=document.verified_at, relevance=relevance, document_version=document.version, published_at=document.published_at or document.issued_at, collected_at=document.collected_at, effective_from=document.effective_from, last_checked_at=document.last_checked_at, freshness_type=freshness, freshness_status=status, document_type=document.document_type, authority_score=authority_score, trust_level=trust_level, trust_reasons=reasons)


def trust_for_document(document: RAGDocument, freshness_status: str | None = None) -> tuple[float, str, list[str]]:
    """Score source authority separately from semantic relevance."""
    domain = document.source_domain or (urlparse(document.source_url).hostname or "").lower()
    official_domain = any(domain == allowed or domain.endswith(f".{allowed}") for allowed in allowed_domains())
    official_publisher = any(name in (document.source_organization or document.publisher) for name in ("법무부", "출입국", "하이코리아", "고용노동부", "최저임금", "노동위원회", "근로복지공단", "전북"))
    score = 0.45
    reasons: list[str] = []
    if official_domain:
        score += 0.25
        reasons.append("허용된 공식 도메인")
    if official_publisher:
        score += 0.15
        reasons.append("공식 발행기관")
    type_bonus = {"law": 0.15, "notice": 0.1, "guide": 0.08, "operational": 0.02, "live": 0.0}.get(document.document_type, 0.04)
    score += type_bonus
    reasons.append({"law": "법령·고시", "notice": "행정 공지", "guide": "공식 안내", "operational": "운영 정보", "live": "실시간 정보"}.get(document.document_type, "검토 문서"))
    if document.status == "fetch_failed" or freshness_status == "최신성 재확인 필요":
        score -= 0.2
        reasons.append("원문 최신성 재확인 필요")
    if document.document_type in {"operational", "live"}:
        score -= 0.12
        reasons.append("실시간 확인 필요")
    score = round(max(0.0, min(1.0, score)), 2)
    level = "high" if score >= 0.8 else "medium" if score >= 0.62 else "low"
    return score, level, reasons


def index_documents(*, documents: tuple[tuple[RAGDocument, list[OfficialChunk]], ...] = SAMPLE_DOCUMENTS, embedding_factory=None) -> tuple[int, int]:
    """Store reviewed documents. Embeddings are optional so development works without an API key."""
    from .database import save_rag_document
    indexed = 0
    skipped = 0
    if embedding_factory is None and settings.openai_api_key:
        try:
            from .embeddings import create_embeddings
            embedding_factory = create_embeddings
        except Exception:
            embedding_factory = None
    for document, chunks in documents:
        embeddings = None
        if embedding_factory and settings.openai_api_key:
            try:
                embeddings = embedding_factory([redact_for_embedding(chunk.text) for chunk in chunks])
            except Exception:
                embeddings = None
        payload = [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks]
        if save_rag_document(document, payload, embeddings):
            indexed += 1
        else:
            skipped += 1
    return indexed, skipped
