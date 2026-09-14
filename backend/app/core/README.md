# app/core/ — 전역 설정·API 스키마

앱 전체가 공유하는 기반 계층입니다. 다른 모든 패키지가 여기에 의존하고, 이 패키지는 다른 패키지에 의존하지 않습니다.

| 파일 | 기능 |
|------|------|
| `config.py` | pydantic-settings 기반 전체 설정(`.env` 로드). RAG 가중치·후보 수·OCR·임베딩 provider·운영 한도 등 환경변수 정의 |
| `schemas.py` | Pydantic 모델 전부 — Guide, Agency, RAGDocument/Chunk/Source, ConsultationRequest/Response, RiskItem, DocumentExplanation 등 API 계약 |
