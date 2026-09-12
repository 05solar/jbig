# frontend/app/ — 페이지와 공용 모듈 (기능별)

App Router 규칙에 따라 **라우트 = 폴더**로 분리되어 있습니다. 각 기능 폴더에 상세 README가 있습니다.

## 루트 파일

| 파일 | 기능 |
|------|------|
| `layout.tsx` | 전역 레이아웃, 메타데이터(JBIG — Jeonbuk International Gateway) |
| `page.tsx` | 홈: 히어로 + 기능 4종을 하나의 블록(구분선)으로 — 전부 실제 페이지로 이동 |
| `globals.css` | 전체 스타일 단일 파일: Pretendard @font-face, 검정 글씨 원칙, 레드 계열 경고 팔레트, 커스텀 드롭다운/스크롤바, 위험 카드, 반응형 |
| `error.tsx` / `not-found.tsx` | 오류·404 화면 (3개 언어 병기) |
| `icon.svg` | 파비콘 (파란 배경 + 다리 모티프) |

## 기능 폴더

| 폴더 | 기능 |
|------|------|
| [`chat/`](./chat/README.md) | AI 상담 챗봇 (멀티턴, 가이드 컨텍스트, 출처 카드) |
| [`guides/`](./guides/README.md) | 상황별 가이드 목록/상세 (13종) |
| [`documents/`](./documents/README.md) | 고용·행정 문서 검토 (업로드→OCR→위험 분석 결과) |
| [`agencies/`](./agencies/README.md) | 지원기관 찾기 (필터 + 위치 기반) |
| [`components/`](./components/README.md) | 공용 컴포넌트 (헤더, 언어 선택, SVG 아이콘) |
| [`lib/`](./lib/README.md) | API 클라이언트·타입, i18n 사전 |
