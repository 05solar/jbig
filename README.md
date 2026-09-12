# JB Bridge AI

전북 거주 외국인 근로자와 유학생을 위한 생성형 AI 정착지원 플랫폼입니다.

> 📚 **문서**: 아키텍처·RAG 파이프라인 설명은 [docs/](./docs/README.md), 각 코드 폴더의 파일별 기능 설명은 폴더 안의 README.md를 참고하세요.

현재 MVP 범위:

- 분야: 체류·행정, 노동
- 기능: 다국어 AI 상담, 상황별 가이드, 행정문서 설명, 맞춤형 기관 연결
- 초기 언어: 한국어, 영어, 베트남어

## 프로젝트 구조

```text
jb-bridge-ai/
├── frontend/   # Next.js 사용자 웹
├── backend/    # FastAPI API
└── docker-compose.yml
```

## 1. 백엔드 실행

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

## 2. 프론트엔드 실행

새 터미널에서 실행합니다.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

웹: http://localhost:3000

## 3. PostgreSQL 실행(선택)

Docker가 설치된 환경에서 실행합니다.

```bash
docker compose up -d db
```

PostgreSQL이 연결되지 않아도 가이드·샘플 RAG 문서로 개발할 수 있습니다. 운영에서는
PostgreSQL/pgvector를 사용해 검토된 문서와 임베딩을 저장하세요.

## 4. 공식 문서 RAG 색인

RAG는 상담 요청마다 웹을 크롤링하지 않습니다. `backend/app/rag.py`에 등록·검토된
공식 문서만 색인하며, URL은 `.env`의 `RAG_ALLOWED_DOMAINS` 허용목록에 있어야 합니다.
현재는 PDF/HWP 자동 수집 대신 정제된 텍스트와 메타데이터를 등록하는 인터페이스와
개발용 샘플 문서를 제공합니다.

```bash
cd backend
source .venv/bin/activate
python -m app.index_rag
```

검토자가 정제한 텍스트 파일을 공식 URL과 함께 등록할 수도 있습니다(명령은 URL을
가져오지 않습니다).

```bash
python -m app.register_rag_document \
  --id moel-example --title "공식 문서 제목" --publisher "고용노동부" \
  --category labor --url https://www.moel.go.kr/ --text-file ./reviewed.txt
```

`initialize_database()`가 기존 테이블을 보존하는 idempotent 마이그레이션을 수행합니다.
새 환경에서는 `python -m app.db_init` 또는 서버 시작 시 `lifespan`에서
`rag_documents`와 `rag_chunks(vector(...))`를 생성합니다. 운영 DB에서는 먼저 백업 후
마이그레이션을 실행하세요.

같은 `document_id`의 콘텐츠 해시가 같으면 저장을 건너뛰고, 내용이 바뀌면 문서와
청크를 갱신합니다. OpenAI 키가 있으면 `EMBEDDING_MODEL`과 `EMBEDDING_DIMENSIONS`로
설정한 임베딩을 pgvector에 저장하고, 상담 시 키워드 결과와 벡터 결과를 결합합니다.
키가 없을 때도 동일한 검토 문서의 안전한 발췌 fallback이 동작합니다.

RAG 관련 주요 환경변수:

```text
RAG_TOP_K=6
RAG_SIMILARITY_THRESHOLD=0.35
RAG_DEBUG_ENABLED=false
RAG_ALLOWED_DOMAINS=law.go.kr,open.law.go.kr,moj.go.kr,immigration.go.kr,hikorea.go.kr,moel.go.kr,minimumwage.go.kr,nlrc.go.kr,comwel.or.kr,jeonbuk.go.kr,liveinkorea.kr
RAG_INDEX_VERSION=1
RAG_ADMIN_TOKEN=
```

관리자 등록 API는 `RAG_ADMIN_TOKEN`이 설정된 경우에만 활성화됩니다.

```bash
curl -X POST http://localhost:8000/api/admin/rag/documents \
  -H "Content-Type: application/json" \
  -H "X-RAG-Admin-Token: $RAG_ADMIN_TOKEN" \
  -d @reviewed-document.json
```

`GET /api/admin/rag/status`로 등록 문서 수와 활성 문서 수를 확인할 수 있습니다.
토큰을 설정하지 않은 개발 환경에서는 관리자 API가 비활성화되며, 기존의 로컬 색인
명령을 사용할 수 있습니다.

## 5. 업데이트형 저장 RAG 운영

상담 요청은 인터넷을 검색하지 않습니다. 검토·색인된 활성 버전만 사용하고, 공식
원문 변경 확인은 별도 CLI 또는 cron에서 실행합니다.

```bash
cd backend
python -m app.cli check-source-updates
python -m app.cli list-pending-updates
python -m app.cli approve-document-version <version-id> --reviewed-by admin --note "검토 완료"
python -m app.cli reject-document-version <version-id> --reviewed-by admin --note "변경 근거 확인 필요"
```

변경이 없으면 마지막 확인 시각만 갱신합니다. 변경이 있으면 기존 활성 버전을
그대로 둔 채 `review_pending` 버전을 생성합니다. 승인 전에는 새 버전이 상담 검색에
들어가지 않으며, 승인 시 새 청크·임베딩을 활성화하고 이전 버전을 `superseded`로
기록한 뒤 색인 버전을 증가시킵니다. 상담 캐시는 색인 버전을 키에 포함하므로 승인
후 이전 RAG 답변이 재사용되지 않습니다.

문서 유형별 기본 점검 주기는 법령 24시간, 공지 6시간, 일반 안내 7일입니다.
`SOURCE_CHECK_INTERVAL_LAW`, `SOURCE_CHECK_INTERVAL_NOTICE`,
`SOURCE_CHECK_INTERVAL_GUIDE`로 변경할 수 있습니다. 운영에서는 cron 예를 들어
다음처럼 실행합니다.

```cron
0 * * * * cd /path/to/web/backend && .venv/bin/python -m app.cli check-source-updates
```

접속 실패 시 기존 문서는 삭제하지 않고 `fetch_failed`와 실패 원인을 기록합니다.
기존 문서는 계속 검색되며 출처에는 최신성 재확인 필요 상태가 표시됩니다.
운영시간·당일 접수 여부처럼 변동성이 큰 정보는 저장형 RAG로 확정하지 않고 공식
사이트 또는 전화로 실시간 확인하도록 안내해야 합니다.

개발용 검색 점검 API는 `RAG_DEBUG_ENABLED=true`일 때만 사용할 수 있습니다.
`GET /api/rag/search?q=숙소비%20공제` 응답은 내부 청크를 최소 메타데이터로 보여주며,
운영 환경에서는 비활성 상태로 두세요.

상담 응답의 `answer_mode`는 `rag`, `ai`, `rules`(기존 호환),
`insufficient_evidence` 등으로 구분됩니다. RAG 응답의 출처 URL·문서명·기관명·확인일은
모델이 생성하지 않고 검색 결과 메타데이터에서 서버가 구성합니다. 근거가 없으면
추측하지 않고 추가 정보 또는 공식기관 확인을 안내합니다.

각 출처에는 의미적 검색 관련도와 별도로 공식 도메인·발행기관·문서 유형·최신성에
기반한 `authority_score`, `trust_level`(`high`/`medium`/`low`)과 판단 이유가 포함됩니다.
법령·고시 등 검증된 공식 자료를 우선하며, 오래 확인되지 않았거나 운영성 정보인
자료는 신뢰도와 최신성 경고를 표시합니다. 신뢰도가 낮은 자료만 검색된 경우에는
확정적인 RAG 답변을 생성하지 않고 공식기관 확인을 안내합니다.

```bash
cd backend
python -m unittest discover -s tests -v
cd ../frontend
./node_modules/.bin/tsc --noEmit
npm run build
```
