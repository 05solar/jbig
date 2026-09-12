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
