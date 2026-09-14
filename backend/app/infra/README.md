# app/infra/ — DB 접근·운영

저장소 접근과 운영(레이트리밋·캐시·예산) 계층입니다. DB가 없어도 앱이 죽지 않도록 전 구간 폴백을 갖습니다.

| 파일 | 기능 |
|------|------|
| `database.py` | PostgreSQL/pgvector 접근 계층 전부(실패 허용·메모리 폴백): 스키마 idempotent 마이그레이션, RAG 문서/청크 저장·lexical 후보 검색(`fetch_lexical_candidates`)·벡터 검색, 버전 승인/거절, 재임베딩, 상담·피드백·AI 예산 저장 |
| `operations.py` | 인메모리 운영 계층: 레이트리밋(슬라이딩 윈도), 상담 캐시, 일일 AI 예산, 지표 집계, IP 해시 |
