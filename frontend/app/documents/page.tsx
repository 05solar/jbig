import { Header } from "../components/header";
import { getLanguage } from "../lib/i18n";
import { DocumentClient } from "./document-client";

export default async function DocumentsPage({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  return <main><Header language={language} /><DocumentClient language={language} /></main>;
}
