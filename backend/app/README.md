# backend/app/ — 애플리케이션 모듈 (기능별)

모듈은 아래 6개 기능 그룹으로 나뉩니다. RAG 파이프라인 상세는 [docs/rag-pipeline.md](../../docs/rag-pipeline.md) 참조.

## ① 코어 (진입점·설정·스키마)

| 파일 | 기능 |
|------|------|
| `main.py` | FastAPI 앱과 **모든 API 엔드포인트**. 상담 파이프라인 오케스트레이션(레이트리밋→캐시→규칙→RAG→답변), 가이드/기관 조회, 문서 분석, 지역 해석, 피드백, RAG 관리자 API. lifespan에서 DB 초기화 + 임베딩 워밍업 |
| `config.py` | pydantic-settings 기반 전체 설정(`.env` 로드). RAG 가중치·후보 수·OCR·임베딩 provider 등 |
| `schemas.py` | Pydantic 모델 전부 — Guide, Agency, RAGDocument/Chunk/Source, ConsultationRequest/Response, RiskItem, DocumentExplanation 등 API 계약 |

## ② RAG (검색·색인·임베딩)

| 파일 | 기능 |
|------|------|
| `rag.py` | RAG 핵심: URL 검증(SSRF 방지), 청크 분할(900자/120 오버랩), 토큰 정규화·동의어 사전(`QUERY_ALIASES`), **공용 DB 하이브리드 검색 `search_rag_db`**(lexical GIN 후보 + pgvector 후보 + 가중 병합 + 안정 랭킹 + TTL 캐시), 증거 선택 `select_evidence`, 권위/최신성 점수, 개발용 `SAMPLE_DOCUMENTS` 25건 |
| `embedding_service.py` | **공용 임베딩 서비스** — local(sentence-transformers)/openai/none provider, lazy singleton, 차원 검증, 실패 시 lexical-only 폴백. 챗봇·OCR·가이드가 모두 이 하나를 사용 |
| `embeddings.py` | 가이드 임베딩 색인(`index_guides`)과 가이드 시맨틱 검색(질문→pgvector 코사인) |
| `updates.py` | 공식 원문 변경 감지(cron용): 안전한 fetch → 해시 비교 → review_pending 버전 생성 |

## ③ 상담 (챗봇)

| 파일 | 기능 |
|------|------|
| `consultation.py` | 결정적 규칙 계층: 언어 감지(한/영/베), 가이드 키워드 매칭(`KEYWORDS`), 기관 연결, 긴급(산재→119) 안내 |
| `ai_consultation.py` | LLM 계층: RAG 근거 답변 생성(관련도·권위 게이트, 민감주제 거부, 증거 선택 적용), 의미적 가이드 분류, grounded 답변, 선택적 쿼리 재작성. 개인정보 마스킹 후 전송, 실패 시 규칙 폴백 |

## ④ 문서 분석 (OCR·위험 검토)

| 파일 | 기능 |
|------|------|
| `document_explanation.py` | 문서 검토 파이프라인: 텍스트 추출→마스킹→유형 분류→주요 조건 추출→**규칙 기반 위험 스크리닝**(위약금·삭감·가산수당·근로시간·연차·주휴·내부규정·최저임금 실계산)→risk_type별 DB RAG 근거 연결→7단 RiskItem(3개 언어 `RISK_TEXTS`)→LLM 요약(OFFICIAL_EVIDENCE 전달, 생성 URL 제거) |
| `ocr.py` | PaddleOCR 로컬 엔진: 이미지 전처리, 스캔 PDF 페이지 렌더링(PyMuPDF), 신뢰도 계산, 저신뢰 재촬영 안내, 엔진 부재 시 폴백 |

## ⑤ 데이터·인프라

| 파일 | 기능 |
|------|------|
| `data.py` | 시드 데이터: 가이드 13종(3개 언어 완역, 대상·실수·관련 공식자료 포함), 기관 5곳 |
| `regions.py` | 전북 14개 시·군 좌표 → 지역명 결정적 해석(외부 지오코딩 API 없음) |
| `database.py` | PostgreSQL 접근 계층 전부(실패 허용·메모리 폴백): 스키마 idempotent 마이그레이션, RAG 문서/청크 저장·후보 검색(`fetch_lexical_candidates`)·벡터 검색, 버전 승인/거절, 재임베딩, 상담·피드백·AI 예산 |
| `operations.py` | 인메모리 운영 계층: 레이트리밋(슬라이딩 윈도), 상담 캐시, 일일 AI 예산, 지표, IP 해시 |

## ⑥ CLI 스크립트

| 파일 | 기능 |
|------|------|
| `cli.py` | RAG 운영: check-source-updates / list-pending-updates / approve·reject-document-version |
| `index_rag.py` | 공식 문서 색인, `--reembed`로 임베딩·토큰 재생성 |
| `embed_guides.py` | 가이드 임베딩, `--reembed` 지원 |
| `db_init.py` | DB 스키마 생성·시드 |
| `register_rag_document.py` | 검토 텍스트 파일 1건 등록 |
