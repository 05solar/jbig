# process.md — 프로젝트 진행 대장

작업(명령) 수행 시마다 이 파일에 간략한 내역을 추가합니다. 규칙은 [agent.md](./agent.md) 참조. 최신 항목이 위.

## 2026-09-14 — 루트 README 개편·실행 화면 스크린샷 추가
- 실제 앱 구동(백엔드 8001·프론트 3000) 후 주요 화면 6종 캡처 → docs/images/ (홈·AI상담 답변·출처 카드·문서검토·가이드·기관찾기)
- 루트 README.md를 프로젝트 소개 중심으로 재작성: 상단 스크린샷, 핵심 원칙(공식정보 기반·출처 제공·개인정보 보호), 기능별 화면 설명, 기술 구성, 하단 실행 방법
- 기존 README의 RAG 운영 상세는 docs/rag-pipeline.md·crawler.md 링크로 정리
- 검증: 캡처 시 브라우저 콘솔 에러 0건, 상담 API 실응답 확인

## 2026-09-14 — backend/app 기능별 패키지 재구성
- 평면 구조였던 backend/app 21개 모듈을 7개 기능 패키지로 분리: core(설정·스키마), data(시드·지역, data.py→seed.py), chat(규칙·LLM 상담), documents(OCR·위험 검토), retrieval(RAG·임베딩·출처 표시·원문 갱신), infra(DB·운영), scripts(운영 CLI 6종). main.py는 uvicorn 진입점(`app.main:app`)이라 루트 유지, crawler/는 기존 유지
- 각 패키지에 역할 설명 README.md·한국어 주석 __init__.py 추가, app/README.md를 구조 인덱스로 개편
- app 내부 상대 import·tests 절대 import·문서(README/docs)의 `python -m app.*` 실행 경로 60개 파일 일괄 수정 (CLI는 `python -m app.scripts.<이름>`으로 변경)
- 검증: hermetic 전체 245개 통과(skip 8), Hit@1/3/5=1.0·MRR=1.0 — 재구성 전 기준선과 동일

## 2026-09-13 — 공식문서 크롤러 도입·RAG 코퍼스 1차 확장 (25→59건)
- app/crawler/ 신설(7모듈): 허용 도메인 전용 fetcher(robots·1초 간격·백오프), HTML/PDF 파서(EUC-KR 감지·메뉴 제거), 관련성/품질 필터, URL·해시 중복제거, 사이트별 SourceSpec, review_pending 등록 파이프라인 + CLI `crawl_official_docs`(--dry-run/--review/--approved-only-index)
- 승인 워크플로 보강: save_pending_rag_version 컬럼 누락 버그 수정, 신규 크롤 문서용 save_crawled_document_pending, 승인 시 자동 로컬 임베딩+search_tokens(index_approved_document), 검수 큐 상세화(품질점수 정렬)
- 1차 실수집: 고용노동부 FAQ·1350 상담·최저임금위·다누리·전북도 5개 사이트 → 후보 45건 등록, 검수 승인 34건·거절 11건(통계/중복/개인사례), 전량 로컬 384차원 임베딩. 표 청크는 벡터 제외(lexical 전용) — MiniLM 허브 벡터 문제 차단, DB 벡터 후보 임계 0.60 분리
- 픽스처 53→92케이스(+39, 한·영·베), Hit@1/3/5=1.0·MRR=1.0 유지. 테스트 207→248개(크롤러 41, 실DB 워크플로·실크롤링 포함), OpenAI 호출 0회
- 문서: docs/crawler.md, app/crawler/README.md, tests/crawler/README.md

## 2026-09-13 — 파일 주석·테스트 폴더 재구성·진행 대장 도입 + 채팅 엔터 버그 수정
- 소스 66개 파일 첫 줄에 한국어 기능 설명 주석 일괄 삽입 (.py/.ts/.tsx/.css)
- backend/tests를 기능별 6개 패키지(rag/chat/documents/data/infra/smoke)로 분리, 각 폴더 README.md·__init__.py 추가, cross-import·fixtures 경로 수정
- 루트에 agent.md(작업 규칙)·process.md(진행 대장), backend/tests/TEST_LOG.md(테스트 대장) 신설
- 채팅 엔터 전송 버그 수정: Windows 한글 IME 조합 확정 Enter(keyCode 229)가 무시되던 문제 → compositionend에서 전송 이어수행
- 검증: 전체 테스트 207개 통과, tsc/빌드 통과

## 2026-09-13 — 출처 표시용 번역 레이어
- RAGSource에 display_title/display_publisher/source_summary(optional) 추가, source_display.py 사전(25문서×en/vi + 기관 5곳)
- 원본 title/publisher/URL 보존, ko는 중복 표시 없음, 챗봇/OCR 공통. 테스트 207개

## 2026-09-13 — 출처 상세 URL 정확성
- 법제처 조문 한글 URL 6건 + 최저임금위 현황 페이지 2건으로 상세화(실존 확인), is_specific_source_url/url_specific 플래그
- generic 출처는 프론트 링크 비활성+안내(홈페이지 오이동 차단). 테스트 196개

## 2026-09-13 — 출력 언어 일관성
- 챗봇 민감주제/키없음/LLM실패 경로의 한국어 evidence 덤프 제거, CHAT_MESSAGES 사전, LLM 언어 규칙 7종+검증(1회 재시도→폴백)
- OCR LLM 요약 언어 검증, vi 누락 메시지 보강, 채팅 오류 문구 사전화. 테스트 188개
- 채팅 UX: 답변 완료 시 답변 시작 지점으로 자동 스크롤

## 2026-09-13 — 가이드 임베딩 공용화·캐시 버전 인식
- 가이드 임베딩을 공용 EmbeddingService(local 384차원)로 통일, embed_guides --reembed, 시그니처 필터로 이종 벡터 혼용 차단
- 검색 캐시 키에 rag_index_version 포함(승인/재색인 시 자동 무효화). 테스트 175개
- docs/ 신설(rag-pipeline/rag-chatbot/rag-document-review) + 폴더별 README 11개

## 2026-09-13 — 로컬 임베딩·DB 후보 검색 최적화
- sentence-transformers(paraphrase-multilingual-MiniLM-L12-v2, 384차원) 공용 임베딩 서비스, lazy singleton/warmup/폴백
- search_rag_db 공용 서비스: GIN search_tokens 후보 + pgvector ANN, 전량 로드 제거(1,025청크 61ms), TTL 캐시, 25청크 재임베딩
- save_rag_document placeholder 버그 수정. 테스트 167개

## 2026-09-13 — OCR 문서분석 DB RAG 전환
- SAMPLE 직접 검색 제거 → PostgreSQL 승인 문서만 근거 사용, DB 장애 시 CHECK 강등(샘플 위장 금지)
- LLM에 OFFICIAL_EVIDENCE 블록 전달, 생성 URL 제거, risk_type별 쿼리(문서당 최대 8회). 실 DB 통합 테스트. 테스트 155개

## 2026-09-13 — 위험 항목 구체화·다국어화 / UI 개편
- 위험 항목 7단 구조(조항/공식기준/문제점/영향/수정안/확인/출처), 최저임금·근로시간 실계산, 기준 문서 7건 추가(코퍼스 25건)
- RISK_TEXTS 3개 언어, 근거 없으면 CHECK 강등. 위험 카드 상단 상태바·레드 경고 팔레트. 테스트 140→146개

## 2026-09-12~13 — PaddleOCR 로컬 OCR 도입
- PaddleOCR(korean) + 스캔 PDF(PyMuPDF), 신뢰도 게이트, 전처리, 한글 경로/oneDNN 이슈 우회
- 신뢰도 미달 시 재촬영 안내, 엔진 부재 시 기존 경로 폴백. 실이미지 통합 테스트. 테스트 131개

## 2026-09-12 — 기능 확장(위치·가이드·문서검토·표준문서)
- 위치 기반 지역 자동 선택(regions.py), 가이드 상세 고도화(13종, 대상/실수/공식자료), 가이드→AI 상담 연결
- 고용문서 위험요소 분석(규칙 기반+RAG 출처), 표준 문서 가이드 섹션. 테스트 115개

## 2026-09-12 — RAG 코퍼스 확장·동점 안정 정렬
- 공식 문서 7→18건, 동의어 확충, _stable_rank(제목→카테고리→권위→최신성→id). Hit@1/3/5=1.0 달성. 테스트 98개

## 2026-09-12 — RAG 검색 고도화
- 가중 하이브리드 병합, 증거 선택, 관련도·권위 게이트, 픽스처 36케이스·메트릭 도입. 테스트 66→98개

## 2026-09-12 — 디자인 개편 / 초기 구축
- Pretendard·SVG 아이콘·JBIG 브랜드·커스텀 드롭다운/스크롤바·반응형, 챗봇 화면 개편
- 저장소 클론, 구조 분석, DESIGN/PROCESS 문서, 로컬 실행 환경(:8001/:3001) 구성
