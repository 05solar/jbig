// 상황별 가이드 목록 화면을 렌더링하는 파일
import Link from "next/link";
import { Header } from "../components/header";
import { Category, getGuides } from "../lib/api";
import { getLanguage, localized, localizedList, messages, withLanguage } from "../lib/i18n";

export default async function GuidesPage({ searchParams }: { searchParams: Promise<{ category?: string; lang?: string }> }) {
  const params = await searchParams;
  const language = getLanguage(params.lang);
  const t = messages[language];
  const selected: Category | undefined = params.category === "residency" || params.category === "labor" ? params.category : undefined;
  const guides = await getGuides(selected);
  const categories = [{ value: undefined, label: t.all }, { value: "residency", label: t.residency }, { value: "labor", label: t.labor }] as const;
  return <main><Header language={language} /><section className="page-heading"><div className="content-width"><div className="eyebrow">SETTLEMENT GUIDES</div><h1>{t.guideTitle}</h1><p>{t.guideDescription}</p></div></section><section className="guide-section content-width"><div className="category-tabs" aria-label={t.guideTitle}>{categories.map(({ value, label }) => { const path = value ? `/guides?category=${value}` : "/guides"; return <Link key={label} className={(!selected && !value) || selected === value ? "active" : ""} href={withLanguage(path, language)}>{label}</Link>; })}</div><div className="result-meta"><strong>{guides.length}</strong> {t.found}</div><div className="guide-grid">{guides.map((guide) => <Link href={withLanguage(`/guides/${guide.id}`, language)} className="guide-card" key={guide.id}><span className={`category-badge ${guide.category}`}>{guide.category === "residency" ? t.residency : t.labor}</span><h2>{localized(guide.title, language)}</h2><p>{localized(guide.summary, language)}</p><div className="card-footer"><span>{t.documents} {localizedList(guide.required_documents, language).length}</span><b>{t.detail}</b></div></Link>)}</div></section></main>;
}
