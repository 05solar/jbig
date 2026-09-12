// 홈 화면(히어로·기능 블록)을 렌더링하는 파일
import Link from "next/link";
import { Header } from "./components/header";
import { IconChat, IconCheck, IconCompass, IconDocument, IconPin } from "./components/icons";
import { featureMessages, getLanguage, messages, withLanguage } from "./lib/i18n";

const features = [
  { href: "/chat", icon: <IconChat size={28} /> },
  { href: "/guides", icon: <IconCompass size={28} /> },
  { href: "/documents", icon: <IconDocument size={28} /> },
  { href: "/agencies", icon: <IconPin size={28} /> },
];

export default async function Home({ searchParams }: { searchParams: Promise<{ lang?: string }> }) {
  const language = getLanguage((await searchParams).lang);
  const t = messages[language];
  return <main>
    <Header language={language} />
    <section className="hero">
      <div className="eyebrow">JEONBUK SETTLEMENT GUIDE</div>
      <h1>{t.heroTitle}<br /><em>{t.heroEmphasis}</em></h1>
      <p>{t.heroDescription.split("\n").map((line) => <span key={line}>{line}<br /></span>)}</p>
      <div className="actions">
        <Link className="primary button-link" href={withLanguage("/chat", language)}>{t.askAi}</Link>
        <Link className="secondary button-link" href={withLanguage("/guides", language)}>{t.viewGuides}</Link>
      </div>
      <div className="trust">{t.trust.split("✓").map((part) => part.trim()).filter(Boolean).map((part) => <span className="trust-item" key={part}><IconCheck size={15} /><b>{part}</b></span>)}</div>
    </section>
    <section className="features">
      <div className="feature-block">
        {featureMessages[language].map(([title, description], index) => (
          <Link className="feature-link" href={withLanguage(features[index].href, language)} key={title}>
            <article>
              <div className="icon">{features[index].icon}</div>
              <h2>{title}</h2>
              <p>{description}</p>
            </article>
          </Link>
        ))}
      </div>
    </section>
  </main>;
}
