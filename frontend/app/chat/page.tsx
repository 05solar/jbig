// AI 상담 페이지 진입(언어·가이드 파라미터 처리)을 담당하는 파일
import { Header } from "../components/header";
import { ChatClient } from "./chat-client";
import { Guide, getGuide } from "../lib/api";
import { getLanguage } from "../lib/i18n";

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ lang?: string; guide?: string }> }) {
  const params = await searchParams;
  const language = getLanguage(params.lang);
  let guide: Guide | null = null;
  if (params.guide) {
    try { guide = await getGuide(params.guide); } catch { guide = null; }
  }
  return <main><Header language={language} /><ChatClient language={language} guide={guide} /></main>;
}
