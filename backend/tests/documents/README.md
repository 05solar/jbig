# tests/documents — 문서 분석(OCR·위험검토) 테스트

| 파일 | 검증 내용 |
|------|-----------|
| test_document_explanation.py | 문서 설명 기본 계약(마스킹·동의·파일 형식) |
| test_document_risks.py | 유형 분류·주요 조건·위험 규칙(수치 비교)·판정 강등·표현 원칙 |
| test_risk_i18n.py | 위험 항목 설명 다국어 일관성(원문·출처 metadata 보존) |
| test_ocr.py | PaddleOCR mock 파이프라인 + 실제 이미지 통합(회전·잘림·흐림·스캔 PDF) |
| test_ocr_db_rag.py | DB RAG 근거 연결(전량 로드 금지·pending 제외·장애 시 SAMPLE 금지) + 실 DB 통합 |
