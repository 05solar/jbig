// 지원기관 찾기 페이지 진입을 담당하는 파일
import { Header } from "../components/header";
import { getLanguage } from "../lib/i18n";
import { AgencyClient } from "./agency-client";

export default async function AgenciesPage({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  return <main><Header language={language} /><AgencyClient language={language} /></main>;
}
