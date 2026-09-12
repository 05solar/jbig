"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";
import { Language } from "../lib/i18n";

export function LanguageSwitcher({ language }: { language: Language }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    if (searchParams.has("lang")) return;
    const saved = localStorage.getItem("jb-bridge-language");
    if (saved === "en" || saved === "vi") {
      const params = new URLSearchParams(searchParams.toString());
      params.set("lang", saved);
      router.replace(`${pathname}?${params}`);
    }
  }, [pathname, router, searchParams]);

  function changeLanguage(next: Language) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "ko") params.delete("lang"); else params.set("lang", next);
    localStorage.setItem("jb-bridge-language", next);
    router.push(`${pathname}${params.size ? `?${params}` : ""}`);
  }

  return <select className="language" value={language} aria-label="Language" onChange={(event) => changeLanguage(event.target.value as Language)}><option value="ko">한국어</option><option value="en">English</option><option value="vi">Tiếng Việt</option></select>;
}
