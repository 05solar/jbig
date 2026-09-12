# tests/rag — RAG 검색·임베딩·출처 테스트

| 파일 | 검증 내용 |
|------|-----------|
| test_rag.py | RAG 기본 계약(검색·출처 서버구성·URL 검증·인젝션 방어·민감주제) |
| test_rag_ranking.py | 가중 병합·권위/최신성 랭킹·증거 선택·게이트·쿼리 재작성 |
| test_rag_retrieval_quality.py | 픽스처 52케이스 Hit@1/3/5·MRR 측정(현재 전부 1.0) |
| test_db_search.py | 로컬 임베딩 provider·DB 후보 검색(전량 로드 금지·상한·캐시·공용 서비스) |
| test_guide_embedding_cache.py | 가이드 임베딩 공용화·캐시 index_version 무효화 |
| test_source_urls.py | 출처 상세 URL 보존·generic 홈페이지 판정 |
| test_source_display.py | 출처 표시용 번역 레이어(원본 보존+en/vi 표시) |
