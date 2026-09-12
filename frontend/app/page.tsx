import Link from "next/link";
import { Header } from "./components/header";
import { featureMessages, getLanguage, messages, withLanguage } from "./lib/i18n";

const icons = ["💬", "🧭", "📄", "📍"];

export default async function Home({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  const t = messages[language];
  return <main><Header language={language} /><section className="hero"><div className="eyebrow">JEONBUK SETTLEMENT GUIDE</div><h1>{t.heroTitle}<br /><em>{t.heroEmphasis}</em></h1><p>{t.heroDescription.split("\n").map((line) => <span key={line}>{line}<br /></span>)}</p><div className="actions"><Link className="primary button-link" href={withLanguage("/chat", language)}>{t.askAi}</Link><Link className="secondary button-link" href={withLanguage("/guides", language)}>{t.viewGuides}</Link></div><div className="trust">{t.trust}</div></section><section className="features">{featureMessages[language].map(([title, description], index) => { const card = <article><div className="icon">{icons[index]}</div><h2>{title}</h2><p>{description}</p></article>; return index === 3 ? <Link className="feature-link" href={withLanguage("/agencies", language)} key={title}>{card}</Link> : <div key={title}>{card}</div>; })}</section></main>;
}
