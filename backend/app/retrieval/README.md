# app/retrieval/ — RAG 검색·임베딩·원문 갱신

검토·승인된 공식문서를 색인하고 검색하는 RAG 계층입니다. 상담 요청마다 웹을 크롤링하지 않고, 등록된 문서만 사용합니다. 파이프라인 상세는 [docs/rag-pipeline.md](../../../docs/rag-pipeline.md) 참조.

| 파일 | 기능 |
|------|------|
| `rag.py` | RAG 핵심: URL 검증(SSRF 방지), 청크 분할(900자/120 오버랩), 토큰 정규화·동의어 사전(`QUERY_ALIASES`), **공용 DB 하이브리드 검색 `search_rag_db`**(lexical GIN 후보 + pgvector 후보 + 가중 병합 + 안정 랭킹 + TTL 캐시), 증거 선택 `select_evidence`, 권위/최신성 점수, 개발용 `SAMPLE_DOCUMENTS` |
| `embedding_service.py` | **공용 임베딩 서비스** — local(sentence-transformers)/openai/none provider, lazy singleton, 차원 검증, 실패 시 lexical-only 폴백. 챗봇·OCR·가이드가 모두 이 하나를 사용 |
| `embeddings.py` | 가이드 임베딩 색인(`index_guides`)과 가이드 시맨틱 검색(질문→pgvector 코사인) |
| `source_display.py` | 출처 카드 표시용 번역(영/베 제목·기관·요약) 사전. 원본 title/publisher/source_url은 절대 교체하지 않는 표시 전용 레이어 |
| `updates.py` | 공식 원문 변경 감지(cron용): 안전한 fetch → 해시 비교 → review_pending 버전 생성 |
