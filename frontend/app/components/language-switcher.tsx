// 언어 선택 커스텀 드롭다운을 담당하는 파일
"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Language } from "../lib/i18n";
import { IconChevronDown, IconGlobe } from "./icons";

const options: { value: Language; label: string }[] = [
  { value: "ko", label: "한국어" },
  { value: "en", label: "English" },
  { value: "vi", label: "Tiếng Việt" },
];

export function LanguageSwitcher({ language }: { language: Language }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (searchParams.has("lang")) return;
    const saved = localStorage.getItem("jb-bridge-language");
    if (saved === "en" || saved === "vi") {
      const params = new URLSearchParams(searchParams.toString());
      params.set("lang", saved);
      router.replace(`${pathname}?${params}`);
    }
  }, [pathname, router, searchParams]);

  useEffect(() => {
    function onOutsideClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutsideClick);
    return () => document.removeEventListener("mousedown", onOutsideClick);
  }, []);

  function changeLanguage(next: Language) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === "ko") params.delete("lang"); else params.set("lang", next);
    localStorage.setItem("jb-bridge-language", next);
    setOpen(false);
    router.push(`${pathname}${params.size ? `?${params}` : ""}`);
  }

  const selected = options.find((option) => option.value === language) ?? options[0];
  return (
    <div className={`custom-select lang-select ${open ? "open" : ""}`} ref={rootRef}>
      <button type="button" className="custom-select-trigger" aria-label="Language" aria-expanded={open} onClick={() => setOpen((state) => !state)}>
        <IconGlobe size={18} />
        {selected.label}
        <IconChevronDown size={15} />
      </button>
      {open && (
        <ul className="custom-select-menu down" role="listbox">
          {options.map((option) => (
            <li key={option.value} role="option" aria-selected={option.value === language} className={option.value === language ? "selected" : ""} onClick={() => changeLanguage(option.value)}>
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
