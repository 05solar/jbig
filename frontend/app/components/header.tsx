import Link from "next/link";
import { Language, messages, withLanguage } from "../lib/i18n";
import { LanguageSwitcher } from "./language-switcher";

export function Header({ language = "ko" }: { language?: Language }) {
  const t = messages[language];
  return (
    <nav className="site-nav">
      <Link href={withLanguage("/", language)} className="brand">JB <span>Bridge</span> AI</Link>
      <div className="nav-links">
        <Link href={withLanguage("/guides", language)}>{t.navGuides}</Link>
        <Link href={withLanguage("/documents", language)}>{language === "ko" ? "문서 설명" : language === "en" ? "Document help" : "Giải thích tài liệu"}</Link>
        <Link href={withLanguage("/agencies", language)}>{language === "ko" ? "기관 찾기" : language === "en" ? "Find support" : "Tìm cơ quan"}</Link>
        <LanguageSwitcher language={language} />
      </div>
    </nav>
  );
}
