# agent.md — 에이전트 작업 규칙

이 저장소에서 AI 에이전트(또는 개발자)가 명령을 수행할 때 지켜야 하는 문서 갱신 규칙입니다.

## 1. process.md 갱신 (필수)

- 루트의 [`process.md`](./process.md)는 프로젝트 진행 내역 대장입니다.
- **명령(작업)을 수행할 때마다** 다음 형식으로 항목을 추가합니다.

```md
## YYYY-MM-DD — 작업 제목
- 수행 내용 요약 (2~5줄)
- 수정/추가 파일 (주요 파일만)
- 검증 결과 (테스트 수·빌드 여부)
```

- 최신 항목이 위로 오도록 작성합니다. 상세 설명은 docs/ 문서에 두고 여기에는 간략히만 적습니다.

## 2. 테스트 기록 갱신 (필수)

- [`backend/tests/TEST_LOG.md`](./backend/tests/TEST_LOG.md)는 테스트 실행 대장입니다.
- **테스트를 실행할 때마다** 실행 범위(전체/부분), 환경(hermetic/실DB), 결과(통과/실패 수·핵심 메트릭)를 한 줄로 추가합니다.
- 실패가 있었던 실행은 원인과 조치도 함께 적습니다.

## 3. 코드 파일 규칙

- 모든 소스 파일(.py/.ts/.tsx/.css) 첫 줄에는 **한국어로 파일의 기능을 설명하는 주석**을 유지합니다. 새 파일을 만들 때도 동일하게 추가합니다.
- 기능 폴더를 새로 만들면 그 폴더에 역할을 설명하는 `README.md`를 함께 둡니다.

## 4. 테스트 실행 표준

```powershell
# hermetic(외부 API·DB 없이) 전체 실행 — 커밋 전 필수
$env:DATABASE_ENABLED="false"; $env:RAG_EMBEDDING_PROVIDER="none"
python -m unittest discover -s tests

# 프론트 검증
tsc --noEmit ; npm run build
```

- 실제 OpenAI API는 테스트에서 호출하지 않습니다(스모크는 `RAG_SMOKE_REAL_API=1`일 때만).

## 5. 문서 위치

- 아키텍처·파이프라인: `docs/` (DESIGN.md, PROCESS.md, rag-*.md)
- 폴더별 파일 설명: 각 폴더의 README.md
- 진행 대장: 루트 `process.md` / 테스트 대장: `backend/tests/TEST_LOG.md`
