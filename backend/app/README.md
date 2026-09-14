# backend/app/ — 애플리케이션 모듈 (기능별 패키지)

기능별 패키지로 분리되어 있으며, 각 폴더의 README.md에 파일별 상세 설명이 있습니다. RAG 파이프라인 상세는 [docs/rag-pipeline.md](../../docs/rag-pipeline.md) 참조.

## 구조

| 폴더/파일 | 기능 | 파일 수 |
|------|------|---------|
| `main.py` | FastAPI 앱과 **모든 API 엔드포인트**. 상담 파이프라인 오케스트레이션(레이트리밋→캐시→규칙→RAG→답변), 가이드/기관 조회, 문서 분석, 지역 해석, 피드백, RAG 관리자 API. lifespan에서 DB 초기화 + 임베딩 워밍업. uvicorn 진입점(`app.main:app`)이라 루트에 위치 | 1 |
| [`core/`](./core/README.md) | 전역 설정(`config.py`)·API Pydantic 스키마(`schemas.py`) | 2 |
| [`retrieval/`](./retrieval/README.md) | RAG 검색·색인(`rag.py`), 공용 임베딩 서비스, 가이드 임베딩, 출처 표시 번역, 원문 변경 감지 | 5 |
| [`chat/`](./chat/README.md) | 챗봇 상담 — 규칙 계층(`consultation.py`)과 LLM 계층(`ai_consultation.py`) | 2 |
| [`documents/`](./documents/README.md) | 문서 분석 — 검토 파이프라인(`document_explanation.py`)과 PaddleOCR(`ocr.py`) | 2 |
| [`data/`](./data/README.md) | 가이드·기관 시드 데이터(`seed.py`)와 전북 지역 해석(`regions.py`) | 2 |
| [`infra/`](./infra/README.md) | PostgreSQL 접근 계층(`database.py`)과 인메모리 운영(`operations.py`) | 2 |
| [`crawler/`](./crawler/README.md) | 공식문서 선별 수집기(목록→상세, robots·rate limit·중복제거·품질점수) — **review_pending으로만 등록**, 승인 후에만 chunk+임베딩 | 7 |
| [`scripts/`](./scripts/README.md) | 운영 CLI(`python -m app.scripts.<이름>`) — DB 초기화·색인·임베딩·크롤링·버전 승인 | 6 |

## 의존 방향

- `core`(설정·스키마)는 최하위 계층으로 다른 패키지에 의존하지 않고, 모든 패키지가 참조합니다.
- `data`는 `core`만 참조합니다.
- 기능 패키지(`chat`·`documents`·`retrieval`·`crawler`)는 `core`·`data`·`infra`를 참조하며, `retrieval`↔`infra` 등 상호 참조는 지연 import로만 이루어집니다(순환 방지).
- `main.py`와 `scripts/`가 최상위에서 각 기능 패키지를 조립합니다.
