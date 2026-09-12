# tests/infra — DB·운영·업데이트 테스트

| 파일 | 검증 내용 |
|------|-----------|
| test_database.py | DB 비활성 시 메모리 폴백 신호 |
| test_operations.py | 레이트리밋(슬라이딩 윈도)·캐시·피드백 집계 |
| test_embeddings.py | 가이드 임베딩 텍스트 계약·주입 클라이언트 경로 |
| test_updates.py | 원문 변경 감지(무변경/변경/중복/실패)·HTML 정규화 |
