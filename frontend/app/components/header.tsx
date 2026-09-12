// 상단 네비게이션(브랜드·중앙 메뉴·언어 선택)을 담당하는 파일
import Link from "next/link";
import { Language, messages, withLanguage } from "../lib/i18n";
import { IconChat, IconCompass, IconDocument, IconPin } from "./icons";
import { LanguageSwitcher } from "./language-switcher";

const menuLabels = {
  ko: { chat: "AI 상담", documents: "문서 설명", agencies: "기관 찾기" },
  en: { chat: "AI chat", documents: "Document help", agencies: "Find support" },
  vi: { chat: "Tư vấn AI", documents: "Giải thích tài liệu", agencies: "Tìm cơ quan" },
} as const;

export function Header({ language = "ko" }: { language?: Language }) {
  const t = messages[language];
  const m = menuLabels[language];
  return (
    <nav className="site-nav">
      <Link href={withLanguage("/", language)} className="brand">
        <strong>JB<span>IG</span></strong>
        <small className="brand-sub">Jeonbuk International Gateway</small>
      </Link>
      <div className="nav-links">
        <Link href={withLanguage("/chat", language)}><IconChat size={19} /><span>{m.chat}</span></Link>
        <Link href={withLanguage("/guides", language)}><IconCompass size={19} /><span>{t.navGuides}</span></Link>
        <Link href={withLanguage("/documents", language)}><IconDocument size={19} /><span>{m.documents}</span></Link>
        <Link href={withLanguage("/agencies", language)}><IconPin size={19} /><span>{m.agencies}</span></Link>
      </div>
      <div className="nav-side">
        <LanguageSwitcher language={language} />
      </div>
    </nav>
  );
}
