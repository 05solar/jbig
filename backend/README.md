# backend/ — FastAPI 백엔드

전북 외국인 정착지원 플랫폼의 API 서버입니다. RAG 검색, AI 상담, OCR 문서 분석, 가이드/기관 데이터 제공을 담당합니다.

| 항목 | 내용 |
|------|------|
| 실행 | `.venv\Scripts\activate` 후 `uvicorn app.main:app --port 8000` |
| 테스트 | `python -m unittest discover -s tests` (외부 API 0회, DB 없이도 통과) |
| 색인 | `python -m app.scripts.index_rag [--reembed]`, `python -m app.scripts.embed_guides [--reembed]` |
| 설정 | `.env` (예시: `.env.example`) — OpenAI 키 없이도 전 기능 동작(로컬 임베딩·규칙 폴백) |

| 폴더/파일 | 기능 |
|-----------|------|
| [`app/`](./app/README.md) | 애플리케이션 모듈 전체 (기능 그룹별 설명은 링크 참조) |
| [`tests/`](./tests/README.md) | 단위·통합 테스트와 픽스처 |
| `requirements.txt` | 의존성 (FastAPI, psycopg, PaddleOCR, sentence-transformers 등) |
| `.env.example` | 전체 환경변수 목록과 기본값 |
