# lib/ — API 클라이언트와 i18n

| 파일 | 기능 |
|------|------|
| `api.ts` | 백엔드 API 계층 전부: 타입 정의(Guide·Agency·ConsultationResponse·RAGSource·RiskItem·DocumentExplanation·RegionInfo)와 fetch 래퍼(가이드/기관/상담/피드백/문서분석/지역해석), `ApiError`(상태코드 보존) |
| `i18n.ts` | 다국어 처리: 지원 언어(ko/en/vi), `localized()` 필드 선택(ko 폴백), `withLanguage()` 링크에 lang 파라미터 유지, UI 메시지 사전(`messages`, `featureMessages`) |
