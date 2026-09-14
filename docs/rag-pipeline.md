# RAG 색인 파이프라인 — 공식 문서 수집·분할·임베딩·저장

이 문서는 공식 문서가 어떤 경로로 들어와서, 어떻게 청크로 나뉘고, 어떻게 임베딩되어 PostgreSQL/pgvector에 저장되는지를 설명합니다. 검색·활용 구조는 [rag-chatbot.md](./rag-chatbot.md)와 [rag-document-review.md](./rag-document-review.md)를 참고하세요.

## 0. 원칙

- **상담·분석 요청은 절대 인터넷을 검색하지 않는다.** 사전에 검토·승인되어 저장된 공식 문서만 사용한다.
- 문서 URL은 허용 도메인 목록(`RAG_ALLOWED_DOMAINS` — 법제처·출입국·하이코리아·고용노동부·최저임금위원회·정부24 등 정부기관 12곳)의 **HTTPS**만 허용하며, 사설 IP는 차단한다(SSRF 방지, `rag.validate_official_url`).
- 출처 메타데이터(제목·발행기관·URL·확인일)는 항상 서버가 DB 값으로 구성한다. LLM은 출처를 생성하지 않는다.

## 1. 공식 문서 수집 (등록 경로 3가지)

문서는 URL을 자동 크롤링하지 않고, **검토자가 정제한 텍스트 + 메타데이터**로 등록됩니다 (`rag.register_document`).

| 경로 | 용도 |
|------|------|
| `python -m app.scripts.register_rag_document --id ... --text-file ...` | 검토 완료 텍스트 파일 등록 (CLI) |
| `POST /api/admin/rag/documents` (X-RAG-Admin-Token) | 운영 중 관리자 등록 (변경 시 review_pending 생성) |
| `app/retrieval/rag.py`의 `SAMPLE_DOCUMENTS` (25건) | 개발용 검토 문서 셋 — `python -m app.scripts.index_rag`로 색인 |

등록 시 부여되는 메타데이터: `document_id`, `title`, `publisher`, `category(residency/labor)`, `document_type(law/notice/guide/operational)`, `source_url/source_domain`, `effective_from/until`, `content_hash`(sha256), `version/version_id`, 점검 주기(`next_check_at` — 법령 24h/공지 6h/안내 7일).

### 변경 감지·승인 workflow (`app/retrieval/updates.py`, `app/scripts/cli.py`)

```
cron: python -m app.scripts.cli check-source-updates
  → 원문 fetch(크기 5MB·리다이렉트 3회 제한) → content_hash 비교
  → 변경 시 review_pending 버전 생성 (활성 버전은 유지)
관리자: approve-document-version → 새 청크·임베딩 활성화, 이전 버전 superseded,
        rag_index_state.index_version += 1  ← 검색·상담 캐시가 이 값을 키에 포함해 자동 무효화
```

## 2. 청크 분할 (`rag.split_chunks`)

- **900자** 단위, **120자 오버랩**
- 경계는 문장 부호(`.`)나 줄바꿈을 우선해 중간 절단을 피함 (chunk_size의 절반 이후에서 탐색)
- 청크 ID: `{document_id}:{index}`, 청크별 `content_hash` 별도 저장
- 현재 검토 문서는 짧아 문서당 1청크가 일반적이나, 장문 법령도 동일 규칙으로 분할됨

## 3. 검색 토큰 정규화 (`rag._tokens` → `rag_chunks.search_tokens`)

색인 시 각 청크에 대해 `title + publisher + text`를 정규화한 **토큰 배열**을 저장합니다. 이 토큰이 DB lexical 후보 검색(GIN 인덱스)의 기반입니다.

- 동의어 사전 `QUERY_ALIASES` (한/영/베 60여 항목): "월급→임금", "비자 연장→체류연장", "gia hạn→체류연장", "not paid→임금체불" 등 — **질의와 문서 양쪽에 동일 적용**되어 의미 일치 보장
- 복합어 규칙: "임금체불→임금", "외국인등록증→등록증" 등 접두 토큰 추가
- 불용어 제거, `[a-z0-9가-힣]{2,}` 토큰화

## 4. 임베딩 (`app/retrieval/embedding_service.py`)

| 항목 | 값 |
|------|-----|
| provider | `RAG_EMBEDDING_PROVIDER` = **local**(기본) / openai / none |
| 로컬 모델 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (한/영/베 교차언어 정렬) |
| 차원 | **384** (pgvector 컬럼과 일치 — `verify_dimension()`이 불일치 시 명시적 오류) |
| 로딩 | 프로세스당 1회 lazy singleton, `RAG_EMBEDDING_WARMUP=true`면 서버 시작 시 preload |
| 실패 시 | 서버는 살아있고 **lexical-only 검색으로 폴백** |
| 시그니처 | `embedding_model` 컬럼에 `local:<모델명>` 저장 — 검색 시 동일 시그니처만 사용해 **다른 provider 벡터와 혼용 차단** |

임베딩 입력은 개인정보 마스킹(`redact_for_embedding`) 후의 청크 텍스트입니다. 챗봇 RAG·OCR 문서 분석·가이드 시맨틱 검색이 **모두 이 하나의 서비스**를 사용합니다.

가이드는 별도로 `guides.embedding`에 저장되며, 임베딩 텍스트는 ko 제목+요약(+en 제목) 압축본입니다(로컬 모델 시퀀스 창 안에 들어가도록).

## 5. 저장 (PostgreSQL/pgvector)

```
rag_documents            문서 원문 + 전체 메타데이터 + status(active/review_pending/superseded/...)
rag_chunks               chunk_id, text, content_hash, embedding vector(384),
                         embedding_model(시그니처), search_tokens text[] (GIN)
rag_document_versions    버전 이력(승인 workflow), rag_version_chunks
rag_index_state          전역 index_version (캐시 무효화 키)
rag_update_audit         변경감지/승인/거절 감사 로그
guides                   가이드 + embedding vector(384) + embedding_model + content_hash
```

## 6. 색인/재임베딩 명령

```bash
python -m app.scripts.index_rag              # SAMPLE_DOCUMENTS 색인 (텍스트+토큰+임베딩)
python -m app.scripts.index_rag --reembed    # 기존 청크의 임베딩·토큰만 재생성 (텍스트/상태/버전 무변경)
python -m app.scripts.embed_guides           # 가이드 임베딩 (content_hash 변경분만)
python -m app.scripts.embed_guides --reembed # 가이드 전체 재임베딩
```

두 명령 모두 실행 전 `verify_dimension()`으로 모델↔pgvector 차원 일치를 검사하며, 차원 변경 마이그레이션은 **비어 있는 컬럼만** 자동 수행하고 데이터가 있으면 명시적 오류를 남깁니다(자동 파괴 금지).
