# 수집 대상 공식 사이트 정의(도메인·목록 URL·상세 링크 패턴·카테고리)를 담당하는 파일
"""Official source specifications, verified against each site's real structure.

Rules baked in here:
- every domain must already be in RAG_ALLOWED_DOMAINS (validate_official_url enforces it)
- comwel.or.kr is intentionally absent: its robots.txt disallows crawling ("Disallow: /")
- 1350.moel.go.kr rtmview pages are MOEL-published anonymized counseling answers
  (the same source type the existing corpus uses); the human review_pending gate
  double-checks for personal data before anything is approved
- gov.kr's foreigner portal now redirects to the JS-rendered plus.gov.kr shell
  (no server-rendered body to extract), so it is deferred to a later pass"""
from __future__ import annotations

from .base import SourceSpec

# moel.go.kr FAQ categories: MC01 임금/퇴직급여, MC02 근로시간/휴게/휴일, MC03 여성/연소자,
# MC04 해고 등, MC05 기타 (목록 -> /faq/faqView.do?seqRepeat=N 상세)
_MOEL_FAQ_LISTS = tuple(
    f"https://www.moel.go.kr/faq/faqList.do?cvlcCtgCd=MC0{index}" for index in range(1, 6)
) + tuple(
    f"https://www.moel.go.kr/faq/faqList.do?cvlcCtgCd=MC0{index}&pageIndex={page}" for index in range(1, 6) for page in (2, 3)
)

SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        key="moel-faq", domain="www.moel.go.kr", publisher="고용노동부", category="labor", document_type="guide",
        list_urls=_MOEL_FAQ_LISTS,
        detail_patterns=(r"/faq/faqView\.do\?[^\"'\s]*seqRepeat=\d+",),
    ),
    # 1350 상담센터의 rtmview 페이지는 고용노동부가 공개 게시한 익명화된 상담 답변으로,
    # 기존 코퍼스도 동일 출처(rtmview.do?id=...)를 사용한다. faqview.do는 JS 렌더링이라 수집 불가.
    # 모든 수집물은 review_pending에서 관리자가 개인정보 여부를 재확인한 뒤에만 승인된다.
    SourceSpec(
        key="moel1350-counsel", domain="1350.moel.go.kr", publisher="고용노동부 고객상담센터", category="labor", document_type="guide",
        list_urls=tuple(f"https://1350.moel.go.kr/rtmlist.do?page={page}&type=ALL" for page in range(1, 4)),
        detail_patterns=(r"rtmview\.do\?[^\"'\s]*id=\d+",),
        onclick_pattern=r"fn_select\('(\d+)'\)",
        onclick_template="https://1350.moel.go.kr/rtmview.do?id={id}",
    ),
    # 최저임금위원회 FAQ는 목록 페이지에 전체 문답이 인라인(아코디언)으로 실려 있어
    # 목록 페이지 자체를 문서로 수집한다. 정책 설명 페이지도 직접 수집 대상.
    SourceSpec(
        key="minimumwage", domain="www.minimumwage.go.kr", publisher="최저임금위원회", category="labor", document_type="notice",
        direct_pages=(
            "https://www.minimumwage.go.kr/customer/faq/list.do",
            "https://www.minimumwage.go.kr/minWage/policy/decisionMain.do",
            "https://www.minimumwage.go.kr/minWage/about/main.do",
            "https://www.minimumwage.go.kr/minWage/process/main.do",
        ),
    ),
    SourceSpec(
        key="liveinkorea", domain="www.liveinkorea.kr", publisher="다누리 한국생활안내(한국건강가정진흥원)", category="residency", document_type="guide",
        list_urls=("https://www.liveinkorea.kr/web/index.do",),
        detail_patterns=(r"/web/lay1/S1T\d+C\d+/contents\.do",),
    ),
    # hikorea.go.kr 안내 페이지는 JS 셸만 서버 렌더링되어 본문 추출이 불가 — 2차 과제로 보류.
    SourceSpec(
        key="jeonbuk-foreigner", domain="www.jeonbuk.go.kr", publisher="전북특별자치도", category="residency", document_type="guide",
        list_urls=("https://www.jeonbuk.go.kr/index.jeonbuk?menuCd=DOM_000000104014000000",),
        detail_patterns=(r"index\.jeonbuk\?menuCd=DOM_000000104014\d+",),
    ),
)


def sources_for(domain: str | None = None, category: str | None = None) -> tuple[SourceSpec, ...]:
    selected = SOURCES
    if domain:
        needle = domain.lower().removeprefix("www.")
        selected = tuple(spec for spec in selected if spec.domain.lower().removeprefix("www.") == needle)
    if category:
        selected = tuple(spec for spec in selected if spec.category == category)
    return selected
