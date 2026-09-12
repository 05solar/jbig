# tests/smoke — 실제 API 스모크(기본 skip)

| 파일 | 검증 내용 |
|------|-----------|
| test_smoke_real_api.py | RAG_SMOKE_REAL_API=1일 때만 실제 OpenAI 호출(임베딩 최대 1회·LLM 최대 2회) |
