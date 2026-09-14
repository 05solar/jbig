# app/crawler/ — 공식문서 선별 수집기

공식기관 사이트에서 체류·노동·행정 안내문서를 **목록→상세** 구조로만 수집하고, 정제·중복제거 후 **review_pending**으로 등록합니다. 크롤러는 절대 active 문서를 만들지 않으며, 임베딩·LLM 호출도 하지 않습니다. 관리자 승인 후에만 chunk+로컬 임베딩이 수행됩니다.

실행: `python -m app.scripts.crawl_official_docs --dry-run` (자세한 옵션은 [docs/crawler.md](../../../docs/crawler.md))

| 파일 | 기능 |
|------|------|
| `base.py` | 공용 자료구조: `SourceSpec`(사이트 정의), `CrawlCandidate`(후보 문서), `CrawlReport`(실행 통계) |
| `fetcher.py` | 예의 갖춘 HTTP 수집기 — 허용 도메인 검증, robots.txt 준수, 호스트별 요청 간격(기본 1초), 429/503 지수 백오프, 동일 URL 재요청 금지, 응답 크기 상한 |
| `parser.py` | HTML 본문 추출(메뉴/푸터/네비 제거, content 컨테이너 우선), 제목·게시일·언어 감지, 링크 수집, PDF 텍스트(pypdf) |
| `filters.py` | 상세 URL 허용/제외 패턴, 카테고리별 관련성 키워드, 무관 페이지(채용/조직도/갤러리 등) 차단, 검수 우선순위용 품질 점수(자동 승인에는 미사용) |
| `dedup.py` | 정규화 URL(세션ID·트래킹 파라미터 제거)·본문 지문·제목+토큰 유사도 기반 중복 제거 |
| `sources.py` | 사이트별 수집 정의 — 실제 구조 확인 후 등록(comwel은 robots 차단으로 제외, 1350 상담사례 게시판은 개인정보 우려로 제외) |
| `pipeline.py` | 오케스트레이션: 목록→상세 수집→필터→중복제거→review_pending 등록(신규=`save_crawled_document_pending`, 변경=`save_pending_rag_version`, 동일=checked_at 갱신)→보고서 |
