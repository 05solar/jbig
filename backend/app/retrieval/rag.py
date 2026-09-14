# RAG 핵심 기능(문서 등록·청크 분할·토큰 정규화·DB 하이브리드 검색·랭킹·증거 선택·출처 구성)을 담당하는 파일
"""Reviewed official-document RAG primitives.

This module deliberately accepts text and metadata rather than fetching URLs. A
separate administrator/import job can call register_document() after review.
"""
from __future__ import annotations

import hashlib
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from ..core.config import settings
from ..core.schemas import Category, RAGDocument, RAGSource

logger = logging.getLogger(__name__)


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


def is_specific_source_url(url: str) -> bool:
    """True when the URL points at a specific document page, not an agency homepage.

    A source link must lead to the actual material used in the answer; a bare
    domain root is treated as generic so the UI can disable the link instead of
    sending users to the wrong page."""
    parsed = urlparse(url)
    return bool(parsed.path.strip("/")) or bool(parsed.query)


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
    if not is_specific_source_url(source_url):
        logger.warning("register_document %s: source_url is a generic homepage (%s); the UI will disable this source link until a specific document URL is provided", document_id, source_url)
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
    register_document(document_id="hikorea-alien-registration", title="외국인등록 신청 안내", publisher="하이코리아", category="residency", source_url="https://www.hikorea.go.kr/", text="한국에 장기 체류하는 외국인은 입국 후 정해진 기간 안에 관할 출입국·외국인관서에 외국인등록을 신청해야 합니다. 여권, 통합신청서, 체류자격별 서류와 수수료를 준비하고 방문 전 예약 필요 여부를 확인합니다. 외국인등록 대상과 기한, 제출서류는 체류자격에 따라 다르므로 1345 또는 하이코리아에서 확인합니다."),
    register_document(document_id="immigration-residence-card-loss-reissue", title="외국인등록증 분실 신고와 재발급", publisher="법무부 출입국·외국인정책본부", category="residency", source_url="https://www.immigration.go.kr/", text="외국인등록증을 분실하거나 훼손한 경우 정해진 기간 안에 관할 출입국·외국인관서에 재발급을 신청해야 합니다. 여권, 통합신청서, 사진, 분실 경위 자료와 수수료를 준비합니다. 재발급 절차와 필요서류는 개인 상황에 따라 다를 수 있으므로 방문 전 하이코리아 또는 1345에서 확인합니다."),
    register_document(document_id="gov24-address-change-report", title="체류지 변경 신고 안내", publisher="정부24", category="residency", source_url="https://www.gov.kr/", text="이사 등으로 체류지가 변경되면 정해진 기간 안에 새로운 체류지의 관할 기관에 체류지 변경 신고를 해야 합니다. 여권과 외국인등록증, 새 주소를 확인할 수 있는 서류를 준비하며, 온라인 신고 가능 여부는 정부24와 하이코리아에서 확인합니다. 신고 기한을 넘기면 불이익이 있을 수 있으므로 이사 후 바로 확인합니다."),
    register_document(document_id="hikorea-stay-extension-application", title="체류기간 연장 허가 신청 절차", publisher="하이코리아", category="residency", source_url="https://www.hikorea.go.kr/", text="체류기간 연장 허가는 체류 만료일 이전에 신청해야 하며, 온라인 전자민원 또는 방문 예약을 통해 접수할 수 있습니다. 여권, 외국인등록증, 통합신청서, 체류자격별 입증서류와 수수료를 준비합니다. 연장 가능 여부와 요건은 체류자격과 개인 사정에 따라 다르므로 1345에서 확인합니다."),
    register_document(document_id="hikorea-status-change-permission", title="체류자격 변경 허가 안내", publisher="하이코리아", category="residency", source_url="https://www.hikorea.go.kr/", text="유학, 취업 등 활동 목적이 바뀌면 새 활동을 시작하기 전에 체류자격 변경 허가를 받아야 합니다. 희망 자격의 요건과 필수 서류를 확인하고 통합신청서와 입증서류, 수수료를 준비합니다. 변경 허가 전에는 현재 체류자격의 활동 범위를 지켜야 하며, 심사 기준은 개인 상황에 따라 다릅니다."),
    register_document(document_id="minimumwage-check-guide", title="최저임금 확인 방법", publisher="최저임금위원회", category="labor", source_url="https://www.minimumwage.go.kr/minWage/policy/decisionMain.do", text="최저임금은 매년 고시되며 원칙적으로 모든 근로자에게 적용됩니다. 근로계약서와 급여명세서에서 기본급과 소정근로시간을 확인하고, 시간당 임금이 해당 연도 최저임금 이상인지 비교합니다. 최저임금에 포함되는 임금 항목은 법령 기준에 따라 판단되므로 불명확하면 고용노동부 1350에 상담합니다."),
    register_document(document_id="moel-overtime-limit", title="연장근로와 근로시간 한도", publisher="고용노동부", category="labor", source_url="https://www.moel.go.kr/", text="법정 근로시간을 넘는 연장근로는 당사자 합의 등 법령상 요건을 갖추어야 하며 한도가 있습니다. 하루 근무시간과 주간 근로시간을 출퇴근기록으로 정리하고, 연장근로 수당이 지급되는지 급여명세서를 확인합니다. 장시간 근로나 수당 미지급이 의심되면 고용노동부 1350 또는 관할 노동관서에 상담합니다."),
    register_document(document_id="moel-holiday-work", title="휴일 근무와 휴일수당", publisher="고용노동부", category="labor", source_url="https://www.moel.go.kr/", text="근로자에게는 법령과 근로계약에 따른 휴일이 보장되며, 휴일 근무에는 가산수당이 적용될 수 있습니다. 휴일에 일한 날짜와 시간을 기록하고 급여명세서에서 수당 지급 여부를 확인합니다. 휴일 부여와 수당 기준은 사업장과 계약 내용에 따라 다르므로 고용노동부 1350에 상담합니다."),
    register_document(document_id="moel-annual-leave", title="연차 유급휴가 사용 안내", publisher="고용노동부", category="labor", source_url="https://www.moel.go.kr/", text="법정 요건을 충족한 근로자는 연차 유급휴가를 사용할 수 있습니다. 근무 기간과 출근율에 따라 연차 일수가 달라지며, 사용하지 못한 연차의 처리 기준은 법령과 근로계약에 따릅니다. 연차 부여 여부가 불명확하면 근로계약서와 출근 기록을 준비해 고용노동부 1350에 확인합니다."),
    register_document(document_id="moel-resignation-severance", title="퇴직 절차와 퇴직금", publisher="고용노동부", category="labor", source_url="https://www.moel.go.kr/", text="퇴직을 결정하면 근로계약과 취업규칙에서 퇴직 통보 방법을 확인하고 서면 기록을 남기는 것이 좋습니다. 정해진 기간 이상 계속 근무한 근로자는 퇴직금 지급 대상이 될 수 있으며, 지급 기한이 지나도 받지 못하면 임금체불로 진정할 수 있습니다. 구체적인 지급 요건은 고용노동부 1350 또는 관할 노동관서에서 확인합니다."),
    register_document(document_id="moel-unpaid-wage-claim", title="임금체불 진정 절차", publisher="고용노동부", category="labor", source_url="https://1350.moel.go.kr/", text="임금체불이 발생하면 미지급 기간과 금액을 정리하고 근로계약서, 급여명세서, 출퇴근기록, 계좌내역을 보관합니다. 사업주에게 지급을 요청한 기록을 남기고, 해결되지 않으면 고용노동부 또는 관할 노동관서에 임금체불 진정을 제기할 수 있습니다. 진정 절차와 필요 서류는 고용노동부 1350에서 안내받을 수 있습니다."),
    register_document(document_id="minimumwage-2026-notice", title="2026년 적용 최저임금 고시", publisher="최저임금위원회", category="labor", source_url="https://www.minimumwage.go.kr/minWage/policy/decisionMain.do", document_type="notice", effective_from="2026-01-01", text="2026년 1월 1일부터 12월 31일까지 적용되는 최저임금 고시 기준은 시간급 10,320원이다. 최저임금 기준은 사업의 종류 구분 없이 모든 사업장에 동일하게 적용된다. 시간급을 해당 연도 최저임금 미만으로 정한 근로계약의 해당 부분은 효력이 인정되지 않을 수 있으므로 계약서와 급여명세서의 시간급을 확인해야 한다."),
    register_document(document_id="moel-overtime-premium-standard", title="연장·야간·휴일근로 가산수당 기준", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제56조", document_type="law", text="상시 5인 이상 사업장에서는 연장근로에 대하여 통상임금의 100분의 50 이상을 가산하여 지급해야 한다. 야간근로(오후 10시부터 다음 날 오전 6시 사이)와 휴일근로에도 가산수당 기준이 적용되며, 휴일근로가 8시간을 초과하면 초과분에 대하여 100분의 100 이상을 가산한다. 상시 5인 미만 사업장에는 가산수당 규정이 적용되지 않으므로 사업장 규모를 함께 확인해야 한다."),
    register_document(document_id="moel-working-hours-standard", title="법정 근로시간과 휴게시간 기준", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제50조", document_type="law", text="1주간의 근로시간은 휴게시간을 제외하고 40시간을 초과할 수 없으며, 1일의 근로시간은 휴게시간을 제외하고 8시간을 초과할 수 없다. 당사자 간에 합의하면 1주 12시간을 한도로 연장근로를 할 수 있다. 사용자는 근로시간이 4시간인 경우 30분 이상, 8시간인 경우 1시간 이상의 휴게시간을 근로시간 도중에 주어야 한다."),
    register_document(document_id="moel-weekly-holiday-standard", title="유급 주휴일 기준", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제55조", document_type="law", text="사용자는 1주 동안의 소정근로일을 개근한 근로자에게 1주에 평균 1회 이상의 유급휴일을 보장해야 한다. 이 유급 주휴일 기준은 4주 평균 1주 소정근로시간이 15시간 미만인 근로자에게는 적용되지 않는다. 주휴일을 무급으로 정한 계약 조항은 이 기준과 충돌할 수 있으므로 확인이 필요하다."),
    register_document(document_id="moel-annual-leave-standard", title="연차 유급휴가 발생 기준", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제60조", document_type="law", text="사용자는 1년간 80퍼센트 이상 출근한 근로자에게 15일의 유급휴가를 주어야 한다. 계속 근로 기간이 1년 미만인 근로자에게는 1개월 개근 시 1일의 유급휴가를 주어야 한다. 이 연차 기준은 상시 5인 이상 사업장에 적용되며, 입사 후 1년 동안 연차가 전혀 없다고 정한 조항은 기준과 충돌할 수 있다."),
    register_document(document_id="moel-wage-cut-penalty-prohibition", title="임금 전액 지급과 위약금 예정 금지", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제43조", document_type="law", text="임금은 통화로 직접 근로자에게 전액을 지급해야 하며, 법령 또는 단체협약에 특별한 규정이 있는 경우가 아니면 일부를 빼고 지급할 수 없다. 사용자가 근로자의 동의 없이 임금을 일방적으로 낮추는 것은 이 기준과 충돌할 수 있다. 또한 근로계약 불이행에 대한 위약금 또는 손해배상액을 미리 정하는 계약은 체결할 수 없다."),
    register_document(document_id="moel-internal-rules-limit", title="취업규칙과 법령의 관계", publisher="고용노동부", category="labor", source_url="https://www.law.go.kr/법령/근로기준법/제96조", document_type="law", text="취업규칙이나 회사 내부규정은 법령이나 해당 사업장에 적용되는 단체협약과 어긋나서는 안 된다. 내부규정이 법령보다 우선한다고 정한 조항이 있어도 강행 법령의 기준을 밑도는 부분은 효력이 인정되지 않을 수 있다. 근로계약 중 법정 기준에 미치지 못하는 부분에도 같은 원칙이 적용된다."),
)


# Deterministic synonym dictionary applied to both queries and documents.
# Longer phrases must appear before their substrings (dict order is preserved).
QUERY_ALIASES = {
    "영문 이름": "이름 정정", "english name": "이름 정정", "student": "유학생",
    "part-time": "시간제취업", "아르바이트": "시간제취업", "음식점": "시간제취업",
    "유학": "유학생", "d-2": "유학생", "working hours": "근로시간", "hours": "근로시간",
    "하루 8시간": "근로시간", "11시간씩": "근로시간", "오래 일": "근로시간",
    "quá nhiều giờ": "근로시간", "근로계약서에는": "근로계약서",
    "근로계약서는": "근로계약서", "근로계약서의": "근로계약서", "근무시간과": "근로시간",
    "근로시간이": "근로시간", "숙소비": "공제", "housing fee": "숙소비",
    "wage deduction": "공제", "임금을": "임금", "임금은": "임금", "임금에서": "임금",
    "돈을 안줘요": "임금체불", "돈을 안줘": "임금체불", "돈을 못": "임금체불",
    "못 받": "임금체불", "안 들어왔": "임금체불", "안들어왔": "임금체불",
    "not paid": "임금체불", "unpaid": "임금체불",
    "minimum wage": "최저임금", "lương tối thiểu": "최저임금",
    "nợ lương": "임금체불", "trả lương": "임금체불", "부당해고": "해고", "해고당": "해고",
    "비자 연장": "체류연장", "visa extension": "체류연장",
    "extend my visa": "체류연장", "extend my stay": "체류연장", "기간을 늘리": "체류연장",
    "gia hạn visa": "체류연장", "gia hạn": "체류연장", "체류기간 연장": "체류연장",
    "체류기간": "체류", "비자": "체류", "visa": "체류",
    "월급": "임금", "봉급": "임금", "salary": "임금", "contract": "근로계약서",
    "주소 변경": "체류지 변경", "주소 바꿨": "체류지 변경", "주소를 바꿔": "체류지 변경",
    "주소 바꿔": "체류지 변경", "이사": "체류지 변경", "địa chỉ": "체류지",
    "잃어버렸": "분실", "다시 만들": "재발급", "mất thẻ": "등록증 분실", "lost": "분실",
    "residence card": "등록증", "외국인등록은": "외국인등록", "외국인등록을": "외국인등록",
    "alien registration": "외국인등록", "đăng ký người nước ngoài": "외국인등록",
    "안 써줘": "서면", "안 써줬": "서면",
    "annual leave": "연차", "nghỉ phép": "연차",
    "그만두": "퇴직", "severance": "퇴직", "quit my job": "퇴직", "thôi việc": "퇴직",
    "holiday": "휴일", "ngày nghỉ": "휴일",
    "tiền nhà": "공제", "실제로는": "실제",
    "fired": "해고", "dismissal": "해고", "sa thải": "해고", "lương": "임금",
    "sinh viên": "유학생", "làm thêm": "시간제취업",
    "기숙사비": "숙소비", "사본": "교부", "52시간": "연장근로 근로시간",
    "address change": "체류지 변경", "report": "신고", "deduct": "공제",
}


def _tokens(text: str) -> set[str]:
    normalized = text.casefold()
    for source, target in QUERY_ALIASES.items():
        normalized = normalized.replace(source, f" {target} ")
    stopwords = {"있습니다", "합니다", "경우", "확인", "관련", "대한", "통해", "자료", "내용", "수", "다를", "다르면", "따라", "것", "있는", "하는", "어떻게", "해야", "하나요"}
    tokens = {token for token in re.findall(r"[a-z0-9가-힣]{2,}", normalized) if token not in stopwords}
    # Preserve useful Korean compound prefixes for matching a question such as
    # "임금을" with a reviewed source titled "임금체불".
    for compound, prefix in (("임금체불", "임금"), ("임금체불", "임금체불"), ("부당해고", "해고"), ("근무시간", "근무"), ("근로계약서", "근로계약서"), ("외국인등록증", "등록증"), ("체류기간", "체류"), ("최저임금", "최저임금"), ("연차", "연차"), ("퇴직금", "퇴직금"), ("퇴직", "퇴직"), ("휴일", "휴일"), ("분실", "분실"), ("재발급", "재발급"), ("연장근로", "연장근로"), ("해고", "해고"), ("휴게", "휴게"), ("야간", "야간"), ("수당", "수당"), ("주휴", "주휴"), ("위약금", "위약금"), ("통합신청서", "통합신청서"), ("교부", "교부"), ("공제", "공제"), ("신고", "신고"), ("주휴수당", "주휴일"), ("주휴일", "주휴일"), ("사회통합프로그램", "사회통합프로그램"), ("지역특화형", "지역특화형")):
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
    _stable_rank(scored, question)
    threshold = settings.rag_similarity_threshold
    return [(chunk, score) for chunk, score in scored if score >= threshold][: limit or settings.rag_top_k]


def indexed_chunks() -> list[OfficialChunk]:
    try:
        from ..infra.database import load_rag_chunks
        stored = load_rag_chunks()
        if stored:
            return [OfficialChunk(document, chunk_id, text, index) for document, chunk_id, text, index in stored]
    except Exception:
        pass
    return _sample_chunks()


def freshness_for_document(document: RAGDocument) -> float:
    """Deterministic 0..1 freshness signal used for ranking, separate from relevance."""
    score = 1.0
    if document.status == "fetch_failed":
        score -= 0.4
    elif document.next_check_at and document.next_check_at < datetime.now(timezone.utc).isoformat():
        score -= 0.3
    if document.document_type in {"operational", "live"}:
        score -= 0.2
    return round(max(0.0, score), 3)


def _ranking_score(chunk: OfficialChunk, relevance: float) -> float:
    """Order results by relevance plus source authority and freshness bonuses.

    The returned relevance shown to users stays untouched; this only ranks."""
    authority, _, _ = trust_for_document(chunk.document)
    return relevance + authority * settings.rag_weight_authority + freshness_for_document(chunk.document) * settings.rag_weight_freshness


def _query_categories(question: str) -> set[str]:
    """Categories the question maps to via the deterministic guide keywords."""
    try:
        from ..chat.consultation import find_guides
        return {guide.category for guide in find_guides(question)}
    except Exception:
        return set()


def _stable_rank(scored: list[tuple[OfficialChunk, float]], question: str) -> list[tuple[OfficialChunk, float]]:
    """Sort by combined ranking score, breaking exact ties deterministically.

    Tie order (never registration order): query-title keyword overlap, query
    category match, authority, freshness, then stable document/chunk id."""
    query_tokens = _tokens(question)
    categories = _query_categories(question)

    def tie_key(item: tuple[OfficialChunk, float]):
        chunk, relevance = item
        authority, _, _ = trust_for_document(chunk.document)
        title_overlap = len(query_tokens & _tokens(chunk.document.title))
        category_match = 1 if chunk.document.category in categories else 0
        return (_ranking_score(chunk, relevance), title_overlap, category_match, authority, freshness_for_document(chunk.document))

    scored.sort(key=lambda item: (item[0].document.document_id, item[0].chunk_index))
    scored.sort(key=tie_key, reverse=True)
    return scored


def merge_scores(lexical: float | None, vector: float | None) -> float:
    """Combine normalized lexical and vector relevance with explicit weights.

    A chunk found by only one signal keeps that signal's score so a missing
    embedding never penalizes reviewed documents."""
    if lexical is not None and vector is not None:
        total = settings.rag_weight_lexical + settings.rag_weight_vector
        if total <= 0:
            return max(lexical, vector)
        return (lexical * settings.rag_weight_lexical + vector * settings.rag_weight_vector) / total
    return lexical if lexical is not None else vector or 0.0


# Short-TTL result cache for repeated queries (document review fires several per upload).
_search_cache: dict[tuple, tuple[float, list]] = {}
_SEARCH_CACHE_TTL_SECONDS = 60.0


def search_rag_db(question: str, *, category: Category | None = None, limit: int | None = None) -> list[tuple[OfficialChunk, float]] | None:
    """Shared PostgreSQL/pgvector hybrid search for the chatbot and document review.

    Small candidate sets come from the DB (GIN token overlap + pgvector ANN);
    the full corpus is never loaded into Python. Scoring, merging, ranking, and
    thresholds reuse the existing policy so search semantics are unchanged.
    Returns None when the database is unreachable."""
    import time as _time
    from . import embedding_service
    from ..infra.database import fetch_lexical_candidates, rag_index_version, search_rag_vectors
    top_k = limit or settings.rag_top_k
    # Index version in the key: approving or re-indexing a document bumps the
    # version (same source the consultation cache uses), invalidating old hits.
    cache_key = (re.sub(r"\s+", " ", question.strip().casefold()), category, top_k, embedding_service.signature(), rag_index_version())
    cached = _search_cache.get(cache_key)
    if cached and _time.time() - cached[0] < _SEARCH_CACHE_TTL_SECONDS:
        return list(cached[1])
    started = _time.perf_counter()
    query_tokens = sorted(_tokens(question))
    t_lex = _time.perf_counter()
    lexical_rows = fetch_lexical_candidates(query_tokens, category, settings.rag_db_lexical_candidates)
    lexical_ms = (_time.perf_counter() - t_lex) * 1000
    t_emb = _time.perf_counter()
    query_vector = embedding_service.embed_text(redact_for_embedding(normalize_text(question)))
    embedding_ms = (_time.perf_counter() - t_emb) * 1000
    vector_rows = None
    vector_ms = 0.0
    if query_vector is not None:
        t_vec = _time.perf_counter()
        vector_rows = search_rag_vectors(query_vector, settings.rag_db_vector_candidates, settings.rag_db_vector_similarity_threshold, model=embedding_service.signature())
        vector_ms = (_time.perf_counter() - t_vec) * 1000
    if lexical_rows is None and vector_rows is None:
        return None
    t_rank = _time.perf_counter()
    candidates = {chunk_id: OfficialChunk(document, chunk_id, text, index) for document, chunk_id, text, index in (lexical_rows or [])}
    lexical = search_official_documents(question, category=category, limit=top_k, chunks=list(candidates.values()))
    merged: dict[str, tuple[OfficialChunk, float | None, float | None]] = {chunk.chunk_id: (chunk, score, None) for chunk, score in lexical}
    for document, chunk_id, text, index, score in (vector_rows or []):
        if category is not None and document.category != category:
            continue
        existing = merged.get(chunk_id)
        merged[chunk_id] = (existing[0], existing[1], score) if existing else (OfficialChunk(document, chunk_id, text, index), None, score)
    scored = [(chunk, round(merge_scores(lex, vec), 3)) for chunk, lex, vec in merged.values()]
    scored = [(chunk, relevance) for chunk, relevance in scored if relevance >= settings.rag_similarity_threshold]
    _stable_rank(scored, question)
    result = scored[:top_k]
    merge_ms = (_time.perf_counter() - t_rank) * 1000
    total_ms = (_time.perf_counter() - started) * 1000
    log = logger.info if settings.rag_debug_enabled else logger.debug
    log("rag_db_search total=%.1fms embedding=%.1fms lexical=%.1fms vector=%.1fms merge=%.1fms candidates=%d results=%d", total_ms, embedding_ms, lexical_ms, vector_ms, merge_ms, len(candidates) + len(vector_rows or []), len(result))
    if len(_search_cache) >= 128:
        _search_cache.pop(min(_search_cache, key=lambda key: _search_cache[key][0]), None)
    _search_cache[cache_key] = (_time.time(), list(result))
    return result


def search_index(question: str, *, category: Category | None = None, limit: int | None = None) -> list[tuple[OfficialChunk, float]]:
    db_result = search_rag_db(question, category=category, limit=limit)
    if db_result is not None:
        return db_result
    # Development fallback (database unreachable): in-memory corpus search.
    lexical = search_official_documents(question, category=category, limit=limit, chunks=indexed_chunks())
    merged: dict[str, tuple[OfficialChunk, float | None, float | None]] = {chunk.chunk_id: (chunk, score, None) for chunk, score in lexical}
    if settings.openai_api_key:
        try:
            from .embeddings import create_embeddings
            from ..infra.database import search_rag_vectors
            vector_matches = search_rag_vectors(create_embeddings([normalize_text(question)])[0], limit or settings.rag_top_k, settings.rag_similarity_threshold)
            for document, chunk_id, text, index, score in vector_matches or []:
                if category is not None and document.category != category:
                    continue
                existing = merged.get(chunk_id)
                merged[chunk_id] = (existing[0], existing[1], score) if existing else (OfficialChunk(document, chunk_id, text, index), None, score)
        except Exception:
            pass
    scored = [(chunk, round(merge_scores(lex, vec), 3)) for chunk, lex, vec in merged.values()]
    scored = [(chunk, relevance) for chunk, relevance in scored if relevance >= settings.rag_similarity_threshold]
    _stable_rank(scored, question)
    return scored[: limit or settings.rag_top_k]


def select_evidence(matches: list[tuple[OfficialChunk, float]], max_evidence: int | None = None) -> list[tuple[OfficialChunk, float]]:
    """Keep only the evidence the answer needs instead of the full top-k.

    Ranked input order is preserved while near-duplicate chunks, excess chunks
    from one document, and anything beyond the context budget are dropped."""
    selected: list[tuple[OfficialChunk, float]] = []
    per_document: dict[str, int] = {}
    seen_tokens: list[set[str]] = []
    budget = max_evidence or settings.rag_max_evidence
    for chunk, score in matches:
        if len(selected) >= budget:
            break
        if per_document.get(chunk.document.document_id, 0) >= settings.rag_max_chunks_per_document:
            continue
        tokens = _tokens(chunk.text)
        if tokens and any(len(tokens & existing) / len(tokens | existing) > 0.85 for existing in seen_tokens if existing):
            continue
        selected.append((chunk, score))
        per_document[chunk.document.document_id] = per_document.get(chunk.document.document_id, 0) + 1
        seen_tokens.append(tokens)
    return selected


def source_from_chunk(chunk: OfficialChunk, relevance: float, language: str = "ko") -> RAGSource:
    document = chunk.document
    freshness = "live_verification_required" if document.document_type in {"operational", "live"} else "versioned"
    status = "최신성 재확인 필요" if document.status == "fetch_failed" or (document.next_check_at and document.next_check_at < datetime.now(timezone.utc).isoformat()) else "최신 공식자료 확인 완료"
    authority_score, trust_level, reasons = trust_for_document(document, status)
    from .source_display import display_fields
    display_title, display_publisher, source_summary = display_fields(document.document_id, document.source_organization or document.publisher, language)
    return RAGSource(document_id=document.document_id, chunk_id=chunk.chunk_id, title=document.title, publisher=document.source_organization or document.publisher, url=document.source_url, url_specific=is_specific_source_url(document.source_url), display_title=display_title, display_publisher=display_publisher, source_summary=source_summary, verified_at=document.verified_at, relevance=relevance, document_version=document.version, published_at=document.published_at or document.issued_at, collected_at=document.collected_at, effective_from=document.effective_from, last_checked_at=document.last_checked_at, freshness_type=freshness, freshness_status=status, document_type=document.document_type, authority_score=authority_score, trust_level=trust_level, trust_reasons=reasons)


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


def is_low_semantic_chunk(text: str) -> bool:
    """Data-table chunks (contact lists, statistics rows) must not get vectors.

    MiniLM embeds keyword-salad tables as near-universal "hub" vectors that
    outrank real answers for unrelated questions; such chunks stay findable
    through lexical search_tokens only."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    # Character-weighted: FAQ pages contain many short label lines (질의/답변 …)
    # but their prose answers dominate by characters; tables do not.
    data_chars = sum(len(line) for line in lines if len(line) <= 14 or re.search(r"\d{2,4}-\d{3,4}-\d{4}", line) or line.isdigit())
    total_chars = sum(len(line) for line in lines)
    return total_chars > 0 and data_chars / total_chars > 0.5


def index_approved_document(document_id: str) -> dict[str, int]:
    """Post-approval step (§17): chunk rows already exist from the approved
    version; fill local embeddings + search_tokens and invalidate the search cache.

    Uses the shared local EmbeddingService only — never the OpenAI API here."""
    from . import embedding_service
    from ..infra.database import embed_document_chunks

    if embedding_service.signature() != "none":
        def embed(texts: list[str]) -> list[list[float] | None] | None:
            vectors = embedding_service.embed_texts([redact_for_embedding(text) for text in texts])
            if vectors is None:
                return None
            return [None if is_low_semantic_chunk(text) else vector for text, vector in zip(texts, vectors)]
    else:
        def embed(texts: list[str]) -> None:
            return None
    summary = embed_document_chunks(document_id, embed, _tokens, embedding_service.signature())
    _search_cache.clear()
    return summary


def index_documents(*, documents: tuple[tuple[RAGDocument, list[OfficialChunk]], ...] = SAMPLE_DOCUMENTS, embedding_factory=None) -> tuple[int, int]:
    """Store reviewed documents. Embeddings are optional so development works without an API key."""
    from ..infra.database import save_rag_document
    indexed = 0
    skipped = 0
    if embedding_factory is None:
        from . import embedding_service
        if embedding_service.signature() != "none":
            embedding_factory = embedding_service.embed_texts
    for document, chunks in documents:
        embeddings = None
        if embedding_factory:
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
