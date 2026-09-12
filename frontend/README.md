# frontend/ — Next.js 사용자 웹 (App Router)

| 항목 | 내용 |
|------|------|
| 실행 | `npm install` → `cp .env.example .env.local` → `npm run dev` |
| 검증 | `./node_modules/.bin/tsc --noEmit` · `npm run build` |
| 스택 | Next.js 16(App Router) + React 19, 외부 UI 라이브러리 없음, Pretendard 폰트 |
| i18n | 라이브러리 없이 메시지 사전 + `?lang=` 파라미터 (ko 기본, en/vi) |

| 폴더/파일 | 기능 |
|-----------|------|
| [`app/`](./app/README.md) | 페이지·컴포넌트·라이브러리 전체 (기능별 설명은 링크 참조) |
| `.env.example` | `NEXT_PUBLIC_API_URL` (백엔드 주소) |
| `next.config.ts` / `tsconfig.json` | 빌드 설정 |
