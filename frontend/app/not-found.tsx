// 404 화면을 렌더링하는 파일
import Link from "next/link";

export default function NotFound() {
  return <main className="state-page"><div className="state-card"><span>404</span><h1>가이드를 찾을 수 없습니다</h1><p>요청한 페이지가 없거나 이동되었습니다.<br />The requested guide could not be found.<br />Không tìm thấy hướng dẫn.</p><Link className="primary button-link state-action" href="/guides">가이드 목록 / Guides</Link></div></main>;
}
