# 공식문서 크롤러 파이프라인

공식기관 사이트에서 체류·노동·행정 안내문서를 **선별 수집**하여, 관리자 검수(review_pending → approve)를 거친 문서만 RAG 코퍼스에 편입하는 파이프라인입니다. 크롤링 자체는 어떤 경우에도 active 문서를 만들지 않으며, OpenAI API를 호출하지 않습니다.

## 전체 흐름

```
sources.py (사이트별 SourceSpec)
  → fetcher.py  목록 페이지 fetch (허용 도메인 검증 · robots.txt · 1초 간격 · 429/503 백오프)
  → parser.py   상세 링크 추출 (href + 게시판 onclick fn_select id)
  → fetcher.py  상세 페이지 fetch (HTML/PDF, 동일 URL 재요청 금지)
  → parser.py   본문 정제 (메뉴/푸터/네비/링크텍스트 제거, EUC-KR 자동 감지, 제목·게시일·언어)
  → filters.py  관련성 키워드 · 최소 본문 300자 · 무관 페이지(채용/조직도/갤러리) 거부
  → dedup.py    정규화 URL(세션ID·트래킹 제거) · 본문 지문 · 제목+토큰 유사도 중복 제거
  → filters.py  품질 점수 0~1 (검수 우선순위 정렬용 — 자동 승인에는 절대 미사용)
  → pipeline.py 등록:
       신규 문서   → save_crawled_document_pending()  (rag_documents inactive + 버전 review_pending)
       변경 문서   → save_pending_rag_version()        (기존 active 버전은 계속 검색 제공)
       동일 문서   → record_rag_check()                (checked_at만 갱신)
```

## 승인 후 색인 (§17)

```
관리자 approve (API /api/admin/rag/versions/{id}/approve 또는 CLI approve-document-version)
  → approve_rag_version()      버전 원자 교체, 이전 버전 superseded, rag_chunks 재구성, index_version +1
  → index_approved_document()  로컬 EmbeddingService(384차원 MiniLM)로 chunk 임베딩 + search_tokens 생성,
                               검색 캐시 무효화
```

- 데이터 표 청크(연락처·통계 목록)는 `is_low_semantic_chunk()` 판정으로 **벡터를 저장하지 않고** lexical 검색으로만 노출됩니다. MiniLM이 표 텍스트를 "만능 허브 벡터"로 임베딩해 무관한 질문까지 상위 노출시키는 문제를 차단합니다.
- DB 청크 벡터 후보는 `RAG_DB_VECTOR_SIMILARITY_THRESHOLD`(기본 0.60) 이상만 사용합니다. 코퍼스 59건 기준 무관 한국어 문장 간 MiniLM 코사인이 0.5~0.6에 몰려 있어, 그 아래는 잡음으로 판단합니다. (기존 병합·랭킹 알고리즘은 수정하지 않음)

## CLI

```powershell
python -m app.scripts.crawl_official_docs --dry-run --domain moel.go.kr --limit 20   # 탐색만, DB 기록 없음
python -m app.scripts.crawl_official_docs --review --category labor --limit 30       # review_pending 등록 (기본 모드)
python -m app.scripts.crawl_official_docs --approved-only-index                      # 승인 문서만 임베딩
# 공통 옵션: --domain --category --limit --since 2025-01-01
```

실행 종료 시 보고서(JSON): visited_urls / detail_pages / accepted_candidates / rejected_irrelevant / rejected_short / rejected_duplicate / generic_urls / robots_blocked / new·updated·unchanged_documents / errors + 도메인별 통계.

## 수집 대상 (1차 검증 완료)

| 사이트 | 방식 | 내용 |
|--------|------|------|
| www.moel.go.kr | FAQ 목록(MC01~05)→faqView 상세 | 고용노동부 자주하는 질문(임금·근로시간·해고·실업급여 등) |
| 1350.moel.go.kr | rtmlist 목록→rtmview 상세(onclick id) | 상담센터 공개 상담 답변 — EUC-KR, 익명화 게시물이지만 검수 단계에서 개인정보 재확인 |
| www.minimumwage.go.kr | 직접 페이지 4종 | 최저임금 제도·심의절차·FAQ(인라인 아코디언)·현황 |
| www.liveinkorea.kr | 메인 메뉴→contents.do 상세 | 다누리 한국생활안내(다문화·정착지원) |
| www.jeonbuk.go.kr | 외국인정책 메뉴→하위 페이지 | 지역특화형 비자·숙련기능인력 추천제·사회통합프로그램 운영기관 |

제외/보류: **comwel.or.kr**(robots.txt `Disallow: /` — 정책 준수로 제외), **hikorea.go.kr / gov.kr(plus.gov.kr)**(JS 렌더링 셸이라 서버측 본문 없음 — 2차 과제), 언론·블로그·민간 사이트(허용 도메인 밖이라 fetcher가 원천 차단).

## 안전 원칙 (§31)

- `validate_official_url()` — RAG_ALLOWED_DOMAINS 밖이면 요청 자체를 하지 않음(리다이렉트 목적지 포함)
- robots.txt Disallow 경로는 수집하지 않음, 호스트당 기본 1초 간격, 429/503 지수 백오프, 응답 5MB 상한
- source_url은 항상 실제 상세 페이지(canonical, 세션/트래킹 파라미터 제거) — 홈페이지 root는 generic으로 거부
- 크롤러 생성 문서는 예외 없이 `status=review_pending, active=false` — 검색(ACTIVE_FILTER)에서 제외
- fetch 실패·변경 감지 시에도 기존 active 문서는 계속 서비스
- 원본 HTML 전체는 저장하지 않고 정제 텍스트+메타데이터만 저장, 주민번호/전화번호는 임베딩 전 마스킹

## 운영 (cron)

크롤러는 웹 요청 안에서 실행하지 않고 별도 CLI/cron으로 실행합니다.

| 주기 | 명령 | 목적 |
|------|------|------|
| daily | `python -m app.scripts.cli check-source-updates` | 등록 문서 원문 변경 감지(법령 24h·공지 6h·가이드 7d 간격은 next_check_at이 관리) |
| weekly | `python -m app.scripts.crawl_official_docs --review --limit 30` | 신규 후보 탐색·등록 |
| 수시 | 관리자 검수 → approve/reject | 승인 시 자동 임베딩·색인 버전 증가 |

## 테스트

- `tests/crawler/` 40개: fetcher 예의 규칙 9, 파서/필터/중복 17, 파이프라인·승인 흐름 9(+2), 실DB 워크플로 3
- 실사이트 스모크는 `RAG_CRAWLER_REAL_TEST=1`일 때만 실행(외부 장애가 CI를 깨지 않도록 격리)
- 코퍼스 확장 후 검색 품질 회귀: fixture 92케이스(검색 78) Hit@1/3/5=1.0, MRR=1.0
