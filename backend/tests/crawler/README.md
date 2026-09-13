# tests/crawler/ — 공식문서 크롤러 테스트

외부 네트워크 없이(주입된 가짜 transport) 크롤러의 안전 규칙을 검증합니다. 실사이트 검증은 별도 플래그로 격리되어 있습니다.

| 파일 | 검증 내용 |
|------|-----------|
| `test_fetcher.py` | 허용 도메인만 요청·비공식/HTTP 거부, robots.txt Disallow 준수, robots 부재 시 허용, 동일 URL 재요청 금지, 429/503 지수 백오프 후 성공, 비지원 콘텐츠 타입 skip, 비공식 도메인 리다이렉트 차단 |
| `test_filters_dedup.py` | 본문 추출(메뉴/푸터 제거)·제목·게시일·언어 감지, 상세 URL 판별, generic root 감지, 제외 경로, 무관 페이지(채용 등) 거부, 품질 점수 정렬, 정규화 URL(세션/트래킹 제거)·중복 URL·중복 해시·유사 본문 거부 |
| `test_pipeline.py` | 목록→상세 수집, 짧은 본문/무관/중복 카운트, dry-run 무기록, 신규→review_pending(active 생성 금지), 변경→pending version, 동일→checked_at만 갱신, source_url path/query 보존, 결정적 document_id, 승인 후 임베딩·캐시 무효화 |
| `test_workflow_db.py` | 실 PostgreSQL: pending은 검색 제외→승인 후 임베딩·색인 버전 증가·검색 노출, reject 시 비활성 유지, 변경 재수집 시 active 유지+2차 pending (DB 미기동 시 자동 skip) |
| `test_crawler_real.py` | 실제 공식 사이트 소수 페이지 스모크(`RAG_CRAWLER_REAL_TEST=1`일 때만, dry-run) |
