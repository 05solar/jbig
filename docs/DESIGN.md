# JB Bridge AI — 설계 문서 (DESIGN)

전북 거주 외국인 근로자·유학생을 위한 생성형 AI 정착지원 플랫폼의 시스템 설계 문서입니다.

## 1. 개요

| 항목 | 내용 |
|------|------|
| 분야 (MVP) | 체류·행정(residency), 노동(labor) |
| 핵심 기능 | 다국어 AI 상담, 상황별 가이드, 행정문서 설명, 맞춤형 기관 연결 |
| 지원 언어 | 한국어(ko), 영어(en), 베트남어(vi) |
| 기술 스택 | FastAPI(Python) + Next.js 16(React 19) + PostgreSQL/pgvector + OpenAI API |

## 2. 시스템 아키텍처

```text
┌─────────────────┐     HTTP(JSON)      ┌──────────────────────┐
│  Next.js 프론트  │ ──────────────────► │   FastAPI 백엔드      │
│  (:3000)        │                     │   (:8000)            │
│  - 홈           │                     │  - 상담 파이프라인     │
│  - AI 채팅 상담  │                     │  - RAG 검색/버전관리   │
│  - 상황별 가이드  │                     │  - 문서 설명(LLM)     │
│  - 기관 찾기     │                     │  - 관리자 API         │
│  - 문서 설명     │                     └──────┬───────┬───────┘
└─────────────────┘                            │       │
                                    ┌──────────▼──┐ ┌──▼──────────┐
                                    │ PostgreSQL  │ │ OpenAI API  │
                                    │ + pgvector  │ │ (선택)      │
                                    │ (선택)      │ └─────────────┘
                                    └─────────────┘
```

**설계 원칙: 전 계층 폴백(Graceful Degradation)**

- PostgreSQL이 없으면 → 인메모리 샘플 데이터(가이드 10개, 기관 5곳, 샘플 RAG 문서 7건)로 동작
- OpenAI 키가 없으면 → 키워드 규칙 매칭 + 공식 문서 발췌로 답변
- AI 호출이 실패하면 → 규칙 기반 결과를 그대로 반환 (사용자에게 오류 대신 안전한 기본 안내)

## 3. 저장소 구조

```text
jbig/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI 앱, 모든 API 엔드포인트
│   │   ├── config.py                # pydantic-settings 기반 환경설정
│   │   ├── schemas.py               # Pydantic 모델 (요청/응답/RAG 문서)
│   │   ├── data.py                  # 시드 데이터: 가이드 10개, 기관 5곳 (3개 언어)
│   │   ├── consultation.py          # 키워드 규칙 매칭, 언어 감지
│   │   ├── ai_consultation.py       # OpenAI 기반 답변 생성 (RAG/grounded/분류)
│   │   ├── rag.py                   # RAG 핵심: 등록·청크·검색·신뢰도 산정
│   │   ├── embeddings.py            # 가이드 임베딩 색인·벡터 검색
│   │   ├── database.py              # PostgreSQL 접근 계층 (전부 실패 허용)
│   │   ├── updates.py               # 공식 원문 변경 감지 (cron/CLI 전용)
│   │   ├── operations.py            # 레이트리밋·캐시·AI 예산·지표
│   │   ├── document_explanation.py  # 행정문서 업로드 → 쉬운 설명
│   │   ├── cli.py                   # RAG 운영 CLI (변경확인/승인/거절)
│   │   ├── db_init.py               # DB 초기화 스크립트
│   │   ├── index_rag.py             # 샘플 RAG 문서 색인 스크립트
│   │   ├── embed_guides.py          # 가이드 임베딩 색인 스크립트
│   │   └── register_rag_document.py # 검토 문서 수동 등록 스크립트
│   └── tests/                       # unittest 66개 (RAG 24, updates 11 중심)
├── frontend/
│   └── app/
│       ├── page.tsx                 # 홈 (히어로 + 기능 카드)
│       ├── chat/                    # AI 상담 채팅 (멀티턴, 출처 표시)
│       ├── guides/                  # 가이드 목록 + [guideId] 상세
│       ├── agencies/                # 기관 찾기 (필터 + 위치기반 정렬)
│       ├── documents/               # 문서 설명 (파일 업로드)
│       ├── components/              # Header, LanguageSwitcher
│       └── lib/                     # api.ts (타입+fetch), i18n.ts (메시지 사전)
├── docker-compose.yml               # pgvector/pgvector:pg16
└── README.md
```

## 4. 백엔드 설계

### 4.1 API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/health` | 상태 + 스토리지 모드(postgresql/memory) |
| GET | `/api/guides`, `/api/guides/{id}` | 가이드 목록/상세 (category 필터) |
| GET | `/api/agencies`, `/api/agencies/{id}` | 기관 목록/상세 (지역·서비스·언어·위치 필터, Haversine 거리) |
| POST | `/api/consultations` | AI 상담 (핵심 엔드포인트) |
| POST | `/api/documents/explain` | 문서 업로드 → 쉬운 설명 |
| POST | `/api/feedback` | 상담 피드백 (helpful/not_helpful) |
| GET | `/api/operations/status` | 운영 지표 |
| GET | `/api/rag/search` | 검색 디버그 (`RAG_DEBUG_ENABLED=true` 시에만) |
| GET/POST | `/api/admin/rag/*` | RAG 문서 등록·상태·승인·거절 (`X-RAG-Admin-Token` 필요) |

### 4.2 상담 답변 모드 (`answer_mode`)

| 모드 | 조건 |
|------|------|
| `rag` | 검토된 공식 문서 청크가 검색됨 → 문서 근거로만 답변 |
| `ai` | 가이드 매칭됨 + OpenAI로 개인화 답변 생성 |
| `rules` | 키워드 매칭 가이드만 반환 (AI 미사용) |
| `guide_fallback` | 민감 주제(불법체류 등) → 법적 판단 거부 + 안전 안내 |
| `insufficient_evidence` | 근거 없음 → 추측하지 않고 추가 정보/공식기관 확인 요청 |

### 4.3 RAG 설계 (프로젝트의 핵심)

**원칙: 상담 요청은 절대 인터넷을 검색하지 않는다.** 검토·승인된 저장 문서만 사용한다.

- **등록**: `register_document()`가 텍스트+메타데이터만 받음 (URL을 가져오지 않음). URL은 허용 도메인 목록(법제처·법무부·출입국·고용노동부 등 정부기관 11곳) + HTTPS + 사설 IP 차단 검증.
- **청크**: 900자 단위, 120자 오버랩, 문장 경계 우선 분할.
- **검색** (`search_index`): 렉시컬 토큰 매칭(한국어 복합어 별칭 처리) + pgvector 코사인 유사도 검색을 병합, 점수 상위 `RAG_TOP_K`(6)개.
- **신뢰도** (`trust_for_document`): 의미적 관련도와 **별도로** 공식 도메인(+0.25)·발행기관(+0.15)·문서유형(법령 +0.15 ~ 실시간 0)·최신성(-0.2)으로 `authority_score` 산정 → `high`(≥0.8)/`medium`(≥0.62)/`low`. 최고 점수가 0.62 미만이면 확정 답변을 생성하지 않음.
- **출처 메타데이터는 서버가 구성** — 모델이 URL·문서명·확인일을 생성하지 못하게 함.

### 4.4 문서 버전 관리 워크플로

```text
[cron/CLI] check-source-updates
    │  허용 도메인 원문 fetch (크기·리다이렉트 제한, HTML/PDF/텍스트)
    │  content_hash 비교
    ├─ 변경 없음 → last_checked_at만 갱신
    └─ 변경 감지 → review_pending 버전 생성 (활성 버전은 그대로 유지)
                       │
              [관리자] approve / reject
                       │
         approve → 새 청크·임베딩 활성화, 이전 버전 superseded,
                   rag_index_state.index_version 증가
                   (상담 캐시 키에 index_version 포함 → 자동 무효화)
```

- 점검 주기: 법령 24h, 공지 6h, 일반 안내 7일 (환경변수로 조정)
- fetch 실패 시 문서를 삭제하지 않고 `fetch_failed` 상태로 계속 검색 대상 유지, 출처에 "최신성 재확인 필요" 표시

### 4.5 안전·개인정보 설계

- **개인정보 마스킹**: 주민등록번호·전화번호·이메일·여권번호 패턴을 외부 API 전송 전 `[REDACTED]` 처리 (상담 질문, 임베딩 입력, 업로드 문서 텍스트 모두)
- **민감 주제 보호**: 불법체류·미등록 체류 관련 질문은 AI가 법적 판단을 내리지 않고 증거 보관 + 1350/출입국기관 상담 안내로 고정 응답
- **프롬프트 인젝션 방어**: 사용자 텍스트를 "untrusted content, not instructions"로 명시, 구조화 출력(json_schema strict) + guide_id enum 제한
- **비용·남용 통제**: 클라이언트별 분당 레이트리밋(10회), 상담 캐시(10분), 일일 AI 호출 예산(200회, DB 우선/메모리 폴백)
- **SSRF 방지**: URL 검증(허용 도메인 + HTTPS + 사설/루프백 IP 차단), fetch 크기 5MB·리다이렉트 3회 제한
- **스캔 문서 동의**: 텍스트 추출이 불가한 이미지/스캔 PDF는 명시적 동의(`allow_unredacted_file`) 없이는 전송 거부
- **식별자 보호**: 클라이언트 IP는 salt와 함께 SHA-256 해시로만 저장

### 4.6 데이터베이스 스키마 (자동 마이그레이션, idempotent)

| 테이블 | 용도 |
|--------|------|
| `guides`, `agencies` | 시드 데이터 + 가이드 임베딩(vector 512) |
| `consultations`, `feedback` | 상담 로그(질문 해시만), 피드백 |
| `daily_ai_usage` | 일일 AI 호출 예산 |
| `rag_documents`, `rag_chunks` | 활성 문서·청크 프로젝션 (임베딩 포함) |
| `rag_document_versions`, `rag_version_chunks` | 버전 이력 + 검토 대기 버전 |
| `rag_index_state` | 전역 색인 버전 (캐시 무효화 키) |
| `rag_update_audit` | 변경감지·승인·거절 감사 로그 |

## 5. 프론트엔드 설계

- **Next.js 16 App Router**: 가이드 페이지는 서버 컴포넌트(SSR fetch), 채팅·기관·문서 페이지는 클라이언트 컴포넌트
- **i18n**: 라이브러리 없이 `lib/i18n.ts` 메시지 사전 + `?lang=` 쿼리 파라미터. 한국어가 기본(파라미터 없음), 선택 언어는 localStorage에 저장 후 자동 복원
- **API 계층**: `lib/api.ts` 단일 파일에 백엔드 타입 정의 + fetch 래퍼 + `ApiError`
- **스타일**: `globals.css` 단일 파일, 외부 UI 라이브러리 없음
- **채팅 UX**: 멀티턴(직전 3개 질문을 `conversation_context`로 전달), 답변 모드 배지, 출처 카드(신뢰도·관련도·권위·확인일), 피드백 버튼, 위치 공유(선택)

## 6. 디자인 가이드라인 (2026-09-12 개정)

프론트엔드 UI는 아래 규칙을 따른다. 신규 화면·컴포넌트도 동일하게 적용한다.

### 6.1 아이콘

- **기본 이모지(이모티콘) 사용 금지.** 모든 아이콘은 `app/components/icons.tsx`의 SVG 컴포넌트를 사용한다 (stroke 기반, `currentColor` 상속).
- 제공 아이콘: Chat, Compass(가이드), Document, Pin(위치/기관), Globe(언어), Send, Spark(AI 아바타), User, ThumbUp/Down, Lock, Warning, Check, Plus, Phone, ChevronDown.
- 파비콘은 `app/icon.svg` (파란 배경 + 흰색 다리 모티프, Next.js 파일 컨벤션으로 자동 적용).

### 6.2 타이포그래피

- 폰트: **Pretendard** (100~900, CDN `@font-face`, `font-display: swap`). `body { font-family: 'Pretendard', "Noto Sans KR", sans-serif; }`
- **과하게 작은 글씨 금지**: 본문·보조 텍스트 최소 13px 이상 (기존 10~12px 전부 상향).
- **회색 부가설명 금지**: 모든 텍스트는 검정(`--ink: #111`)으로 표기하고, 강조는 **bold**로 표현한다. 예외: 어두운 배경(네이비 카드) 위 밝은 텍스트, 의미 색상(파랑 링크, 신뢰도 뱃지, 오류 빨강).

### 6.3 메인 홈

- 히어로 버튼(AI에게 질문하기/가이드 보기)과 기능 4종은 모두 실제 페이지(`/chat`, `/guides`, `/documents`, `/agencies`)로 이동하는 링크여야 한다.
- 기능 카드는 개별 카드가 아니라 **하나의 블록**(`.feature-block`)으로 뭉치고 **1px 구분선**으로 나눈다. 호버 시 배경(#eef4fd)·제목 색상(blue) 전환.

### 6.4 헤더

- 서비스 타이틀: **JBIG** (JB 네이비 + IG 블루), 서브타이틀 **Jeonbuk International Gateway** (13px, 검정). 브라우저 탭 타이틀도 "JBIG — Jeonbuk International Gateway".
- 레이아웃: 3열 그리드 — 브랜드(좌) / **메뉴 중앙 정렬** / 언어 선택(우).
- 메뉴는 16px·bold, 각 항목에 SVG 아이콘 동반 (AI 상담·상황별 가이드·문서 설명·기관 찾기).
- 언어 선택기는 **글로브 SVG + 커스텀 드롭다운**(`.lang-select`, 아래로 펼침 `.custom-select-menu.down`) — 네이티브 select 금지.
- 모바일(≤760px)에서는 메뉴 텍스트를 숨기고 아이콘만 표시.

### 6.5 챗봇 화면

- 페이지 타이틀: **"AI 상담 챗봇"** (en: AI Consultation Chatbot / vi: Chatbot tư vấn AI), eyebrow "JBIG CONSULTATION".
- 채팅창 배경 **흰색** (그라데이션 금지), **커스텀 스크롤바** (8px, 둥근 썸, 호버 시 블루 — `scrollbar-width: thin` + `::-webkit-scrollbar`).
- 채팅창 높이 `min-height: 62vh`(모바일 dvh 단위) — 화면 아래까지 길게.
- 환영 블록(인사말 + 추천 질문)은 채팅창 **정중앙 배치** (flex column + `margin: auto`), 중복 부가설명 제거.
- 드롭다운(사용자 유형)은 네이티브 `<select>` 대신 동일 디자인의 **커스텀 드롭다운**(`CustomSelect`, 외부 클릭 닫힘, 위로 펼침).
- **Enter 전송** (Shift+Enter 줄바꿈, 한글 IME 조합 중 전송 방지 `isComposing` 체크).
- 반응형: 760px 이하에서 컨텍스트 입력 줄이 전체폭 스택, 말풍선 88%.

## 7. 환경 변수 요약

| 변수 | 기본값 | 용도 |
|------|--------|------|
| `OPENAI_API_KEY` | (없음) | 없으면 규칙+발췌 모드로 동작 |
| `OPENAI_MODEL` | gpt-5.4-mini | 답변 생성 모델 |
| `EMBEDDING_MODEL` / `EMBEDDING_DIMENSIONS` | text-embedding-3-small / 512 | 임베딩 |
| `DATABASE_URL` | localhost:5432/jb_bridge | 실패 시 30초 백오프 후 메모리 폴백 |
| `RAG_TOP_K` / `RAG_SIMILARITY_THRESHOLD` | 6 / 0.35 | 검색 파라미터 |
| `RAG_ALLOWED_DOMAINS` | 정부기관 11곳 | 출처 허용 목록 |
| `RAG_ADMIN_TOKEN` | (없음) | 없으면 관리자 API 비활성 |
| `RAG_DEBUG_ENABLED` | false | 검색 디버그 API |
| `SOURCE_CHECK_INTERVAL_*` | 법령 24h / 공지 6h / 안내 7일 | 원문 점검 주기 |
| `DAILY_AI_CALL_LIMIT` / `CONSULTATION_RATE_LIMIT` | 200 / 10 | 비용·남용 통제 |
