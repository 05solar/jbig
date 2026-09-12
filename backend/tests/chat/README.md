# tests/chat — 챗봇 상담 테스트

| 파일 | 검증 내용 |
|------|-----------|
| test_consultation.py | 언어 감지·키워드 가이드 매칭(3개 언어)·긴급 안내 |
| test_ai_consultation.py | LLM 경로(마스킹·store=false·폴백·의미 분류 게이트) |
| test_consultation_e2e.py | POST /api/consultations E2E 10개 시나리오(mock) |
| test_output_language.py | 출력 언어 일관성(선택 언어 강제·원문 보존·재현 질문) |
