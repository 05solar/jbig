# app/scripts/ — 운영 CLI 스크립트

전부 `python -m app.scripts.<이름>` 형태로 backend/ 디렉터리에서 실행합니다.

| 파일 | 실행 | 기능 |
|------|------|------|
| `cli.py` | `python -m app.scripts.cli <command>` | RAG 운영: check-source-updates / list-pending-updates / approve·reject-document-version(승인 시 자동 임베딩) |
| `crawl_official_docs.py` | `python -m app.scripts.crawl_official_docs` | 공식문서 크롤링: `--dry-run`(탐색만) / `--review`(review_pending 등록) / `--approved-only-index`(승인 문서 임베딩), `--domain --category --limit --since` |
| `index_rag.py` | `python -m app.scripts.index_rag [--reembed]` | 공식 문서 색인, `--reembed`로 임베딩·토큰만 재생성 |
| `embed_guides.py` | `python -m app.scripts.embed_guides [--reembed]` | 가이드 임베딩 생성/재생성 |
| `db_init.py` | `python -m app.scripts.db_init` | DB 스키마 생성·시드 적재 |
| `register_rag_document.py` | `python -m app.scripts.register_rag_document` | 검토 완료 텍스트 파일 1건을 RAG 문서로 등록 |
