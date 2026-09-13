# backend/tests/ — 테스트 (248개, 외부 API 0회)

기능별 패키지로 분리되어 있으며, 각 폴더의 README.md에 파일별 검증 내용이 있습니다. 테스트 실행 내역은 [TEST_LOG.md](./TEST_LOG.md)에 기록합니다.

실행: `python -m unittest discover -s tests` (hermetic 권장 env: `DATABASE_ENABLED=false`, `RAG_EMBEDDING_PROVIDER=none`)

## 구조

| 폴더 | 내용 | 파일 수 |
|------|------|---------|
| [`rag/`](./rag/README.md) | RAG 검색·랭킹·임베딩·출처(URL/표시 번역) | 7 |
| [`chat/`](./chat/README.md) | 챗봇 상담(규칙·LLM·E2E·출력 언어) | 4 |
| [`documents/`](./documents/README.md) | 문서 분석(OCR·위험검토·다국어·DB 근거) | 5 |
| [`crawler/`](./crawler/README.md) | 공식문서 크롤러(수집 규칙·중복제거·승인 워크플로·실크롤링) | 5 |
| [`data/`](./data/README.md) | 가이드·기관·지역 시드 데이터 | 3 |
| [`infra/`](./infra/README.md) | DB 폴백·운영·가이드 임베딩·원문 갱신 | 4 |
| [`smoke/`](./smoke/README.md) | 실제 API 스모크(기본 skip) | 1 |

## 루트 공용 파일

| 파일 | 기능 |
|------|------|
| `fakes.py` | 결정적 fake(해시 임베딩·FakeLLMClient·FailingLLMClient) — 모든 패키지가 공용 |
| `fixtures/rag_cases.json` | 검색 품질 픽스처 92케이스(체류/행정/노동/범위외, 한·영·베) |
| `TEST_LOG.md` | 테스트 실행 대장(실행 시마다 갱신) |
