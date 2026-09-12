# backend/tests/ — 테스트 (175개, 외부 API 0회)

모든 테스트는 OpenAI API·인터넷 없이 통과합니다(mock/fixture/결정적 fake). 실 DB 통합 테스트는 PostgreSQL이 떠 있을 때만 실행되고 아니면 skip됩니다.

실행: `python -m unittest discover -s tests` (hermetic 실행 권장 env: `DATABASE_ENABLED=false`, `RAG_EMBEDDING_PROVIDER=none`)

## 공용 인프라

| 파일 | 기능 |
|------|------|
| `fakes.py` | 결정적 fake: 해시 기반 fake embedding, FakeLLMClient(요청 캡처), FailingLLMClient |
| `fixtures/rag_cases.json` | 검색 품질 픽스처 **52케이스**(체류/행정/노동/범위외, 한·영·베) — 기대 문서·가이드·answer_mode·최소 점수 |

## RAG·검색

| 파일 | 검증 내용 |
|------|-----------|
| `test_rag.py` | RAG 기본 계약: 검색·출처 서버구성·비활성 문서 제외·URL 검증·프롬프트 인젝션 방어·민감주제 거부 |
| `test_rag_retrieval_quality.py` | 픽스처 기반 **Hit@1/3/5·MRR 측정**(현재 전부 1.0), 범위외 무매치, 무관 문서 상위 금지 |
| `test_rag_ranking.py` | 가중 병합·권위/최신성 랭킹·증거 선택(중복 제거·상한)·관련도 게이트·쿼리 재작성 mock |
| `test_db_search.py` | 로컬 임베딩 provider(안정성·singleton·차원 오류·none 폴백), DB 후보 검색(상한 준수·5,000청크에서도 전량 로드 금지·hybrid 병합 동일성·공용 서비스·캐시) |
| `test_guide_embedding_cache.py` | 가이드 임베딩의 공용 서비스 사용(OpenAI 0호출)·시그니처 필터, **캐시 index_version 무효화**, ko/en/vi 가이드 분류 |

## 상담·문서 분석

| 파일 | 검증 내용 |
|------|-----------|
| `test_consultation.py` | 언어 감지, 키워드 가이드 매칭(3개 언어), 긴급 안내, 복합 질문 |
| `test_ai_consultation.py` | LLM 경로: 마스킹, store=false, 실패 폴백, 의미 분류 confidence 게이트 |
| `test_consultation_e2e.py` | `POST /api/consultations` E2E 10시나리오(정상 RAG/근거부족/권위부족/키없음/LLM장애/예산초과/캐시/색인버전/베트남어/범위외) |
| `test_document_risks.py` | 문서 유형 분류·주요 조건·위험 규칙(수치 비교 포함)·근거 부재 시 판정 강등·위법 확정 표현 금지 |
| `test_risk_i18n.py` | 위험 설명 다국어 일관성(en/vi에 한국어 잔존 금지, 원문 조항·출처 메타데이터는 원본 유지) |
| `test_ocr.py` | OCR: mock 파이프라인 + **실제 PaddleOCR 통합**(생성 한글 계약서 이미지, 회전·잘림·흐림·빈 이미지·스캔 PDF) |
| `test_ocr_db_rag.py` | 문서 분석의 DB RAG 근거: DB 후보 사용·전량 로드 금지·pending 제외·장애 시 SAMPLE 폴백 금지·OFFICIAL_EVIDENCE 전달·생성 URL 제거 + **실 DB 통합** |

## 데이터·기타

| 파일 | 검증 내용 |
|------|-----------|
| `test_guides.py` / `test_agencies.py` | 시드 데이터 무결성(13가이드/5기관, 3개 언어), 필터·거리 정렬 |
| `test_regions.py` | 좌표→전북 시·군 해석, 도외 처리, API 검증 |
| `test_database.py` / `test_operations.py` | DB 폴백 신호, 레이트리밋·캐시·피드백 |
| `test_embeddings.py` | 가이드 임베딩 텍스트 계약, 주입 클라이언트 경로 |
| `test_updates.py` | 원문 변경 감지: 무변경/변경/중복/실패 처리, HTML 정규화 |
| `test_document_explanation.py` | 문서 설명 기본 계약(마스킹, 동의, 파일 형식) |
| `test_smoke_real_api.py` | 선택적 실 API 스모크 — `RAG_SMOKE_REAL_API=1`일 때만(기본 skip) |
