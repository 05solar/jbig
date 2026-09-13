# JB Bridge AI — 문서 목록

프로젝트 구조와 RAG 파이프라인을 설명하는 문서 모음입니다.

| 문서 | 내용 |
|------|------|
| [DESIGN.md](./DESIGN.md) | 시스템 아키텍처, 저장소 구조, API, DB 스키마, 디자인 가이드라인 |
| [PROCESS.md](./PROCESS.md) | 기능별 처리 흐름도(mermaid): 상담 파이프라인, 문서 수명주기, 운영 |
| [rag-pipeline.md](./rag-pipeline.md) | **공식 문서 수집 → 청크 분할 → 토큰/임베딩 → 저장** 색인 파이프라인 |
| [rag-chatbot.md](./rag-chatbot.md) | **챗봇**이 RAG를 활용하는 구조: 하이브리드 검색, 랭킹, 증거 선택, 답변 모드 |
| [rag-document-review.md](./rag-document-review.md) | **OCR 문서 분석**이 RAG를 활용하는 구조: 위험 규칙 → DB 근거 → 기준 비교 |
| [crawler.md](./crawler.md) | **공식문서 크롤러**: 선별 수집 → 정제·중복제거 → review_pending → 승인 후 임베딩 |

## 폴더별 파일 설명

각 코드 폴더에는 그 폴더의 파일들이 어떤 기능을 하는지 설명하는 README.md가 있습니다.

- [backend/README.md](../backend/README.md) — 백엔드 전체 구성
- [backend/app/README.md](../backend/app/README.md) — 애플리케이션 모듈(기능 그룹별)
- [backend/tests/README.md](../backend/tests/README.md) — 테스트 구성
- [frontend/README.md](../frontend/README.md) — 프론트엔드 전체 구성
- [frontend/app/README.md](../frontend/app/README.md) — 페이지·컴포넌트·라이브러리
