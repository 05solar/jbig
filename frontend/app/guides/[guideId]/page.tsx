// 가이드 상세 화면(절차·서류·실수·공식자료·AI 상담 연결)을 렌더링하는 파일
import Link from "next/link";
import { notFound } from "next/navigation";
import { Header } from "../../components/header";
import { ApiError, getAgencies, getGuide } from "../../lib/api";
import { getLanguage, localized, localizedList, messages, withLanguage } from "../../lib/i18n";
import { IconChat, IconCheck, IconPhone, IconWarning } from "../../components/icons";

const detailCopy = {
  ko: { target: "누구를 위한 가이드인가요", mistakes: "자주 발생하는 실수", officialDocs: "관련 공식자료", askAi: "AI 상담으로 자세히 알아보기" },
  en: { target: "Who this guide is for", mistakes: "Common mistakes", officialDocs: "Related official materials", askAi: "Ask the AI about this guide" },
  vi: { target: "Hướng dẫn này dành cho ai", mistakes: "Lỗi thường gặp", officialDocs: "Tài liệu chính thức liên quan", askAi: "Hỏi AI về hướng dẫn này" },
} as const;

export default async function GuideDetailPage({ params, searchParams }: { params: Promise<{ guideId: string }>; searchParams: Promise<{ lang?: string }> }) {
  const [{ guideId }, query] = await Promise.all([params, searchParams]);
  const language = getLanguage(query.lang);
  const t = messages[language];
  let guide;
  try { guide = await getGuide(guideId); } catch (error) { if (error instanceof ApiError && error.status === 404) notFound(); throw error; }
  const agencies = (await getAgencies()).filter((agency) => guide.agency_ids.includes(agency.id));
  const d = detailCopy[language];
  const steps = localizedList(guide.steps, language);
  const documents = localizedList(guide.required_documents, language);
  const cautions = localizedList(guide.cautions, language);
  const target = guide.target?.[language] || guide.target?.ko || "";
  const mistakes = guide.common_mistakes?.[language] || guide.common_mistakes?.ko || [];
  return <main><Header language={language} /><div className="detail-layout content-width"><Link href={withLanguage("/guides", language)} className="back-link">{t.back}</Link><header className="detail-header"><span className={`category-badge ${guide.category}`}>{guide.category === "residency" ? t.residency : t.labor}</span><h1>{localized(guide.title, language)}</h1><p>{localized(guide.summary, language)}</p>{target && <p><b>{d.target}:</b> {target}</p>}</header><div className="detail-columns"><div className="detail-main"><section className="detail-card"><h2>{t.steps}</h2><ol className="steps">{steps.map((step, index) => <li key={step}><span>{index + 1}</span><p>{step}</p></li>)}</ol></section><section className="detail-card"><h2>{t.documents}</h2><ul className="check-list">{documents.map((item) => <li key={item}><IconCheck size={15} />{item}</li>)}</ul></section><section className="detail-card caution"><h2>{t.caution}</h2><ul>{cautions.map((item) => <li key={item}>{item}</li>)}</ul></section>{mistakes.length > 0 && <section className="detail-card"><h2><IconWarning size={18} /> {d.mistakes}</h2><ul className="mistake-list">{mistakes.map((item) => <li key={item}>{item}</li>)}</ul></section>}<Link className="primary button-link guide-chat-cta" href={withLanguage(`/chat?guide=${guide.id}`, language)}><IconChat size={18} />{d.askAi}</Link></div><aside><section className="detail-card"><h2>{t.help}</h2>{agencies.map((agency) => <div className="agency" key={agency.id}><h3>{localized(agency.name, language)}</h3><p>{localized(agency.description, language)}</p><a href={`tel:${agency.phone}`}><IconPhone size={14} />{agency.phone}</a><a href={agency.website} target="_blank" rel="noreferrer">{t.website}</a></div>)}</section>{guide.related_documents?.length > 0 && <section className="detail-card"><h2>{d.officialDocs}</h2><ul className="reference-list">{guide.related_documents.map((reference) => <li key={reference.url + reference.title}><a href={reference.url} target="_blank" rel="noreferrer"><b>{reference.title}</b><small>{reference.publisher} ↗</small></a></li>)}</ul></section>}<section className="source-card"><span>{t.source}</span><a href={guide.source_url} target="_blank" rel="noreferrer">{localized(guide.source_name, language)} ↗</a><small>{t.verified} {guide.verified_at}</small></section></aside></div></div></main>;
}
