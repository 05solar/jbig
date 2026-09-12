// 문서 검토 페이지 진입을 담당하는 파일
import { Header } from "../components/header";
import { getLanguage } from "../lib/i18n";
import { DocumentClient } from "./document-client";

export default async function DocumentsPage({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  return <main><Header language={language} /><DocumentClient language={language} /></main>;
}
