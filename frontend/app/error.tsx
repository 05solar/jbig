// 전역 오류 화면을 렌더링하는 파일
"use client";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return <main className="state-page"><div className="state-card"><span>!</span><h1>서비스에 연결할 수 없습니다</h1><p>잠시 후 다시 시도해 주세요.<br />Unable to connect. Please try again shortly.<br />Không thể kết nối. Vui lòng thử lại sau.</p><button className="primary state-action" onClick={reset}>다시 시도 / Retry</button></div></main>;
}
