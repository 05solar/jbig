import { Header } from "../components/header";
import { ChatClient } from "./chat-client";
import { getLanguage } from "../lib/i18n";

export default async function ChatPage({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  return <main><Header language={language} /><ChatClient language={language} /></main>;
}
