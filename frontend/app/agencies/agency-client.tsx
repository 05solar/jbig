// 지원기관 검색 UI(필터·위치 기반 정렬·지역 감지)를 담당하는 파일
"use client";

import { useCallback, useEffect, useState } from "react";
import { Agency, getAgencies, RegionInfo, resolveRegion } from "../lib/api";
import { Language, localized } from "../lib/i18n";
import { IconCheck, IconGlobe, IconPin } from "../components/icons";

const copy = {
  ko: { title: "내게 맞는 지원기관 찾기", description: "필요한 도움을 선택하고, 현재 위치에서 가까운 기관을 확인하세요.", all: "전체 서비스", immigration: "체류·행정", labor: "노동·임금", accident: "산업재해", interpretation: "통역·생활", languageOnly: "한국어 지원 기관만", location: "현재 위치로 거리순", locating: "위치 확인 중…", reset: "위치 해제", count: "개 기관", empty: "조건에 맞는 기관이 없습니다.", error: "기관 정보를 불러오지 못했습니다.", denied: "위치 권한을 허용하면 현재 지역을 자동으로 선택할 수 있습니다.", call: "전화", site: "웹사이트", map: "지도", distance: "km", language: "선택 언어 지원", hours: "운영시간", verified: "정보 확인일", approximate: "거리는 등록된 대표 위치 기준의 참고값입니다.", currentRegion: "현재 지역" },
  en: { title: "Find the right support", description: "Choose the help you need and find nearby support agencies.", all: "All services", immigration: "Immigration", labor: "Labor & wages", accident: "Work accident", interpretation: "Interpretation & life", languageOnly: "English support only", location: "Sort by my location", locating: "Finding location…", reset: "Clear location", count: "agencies", empty: "No agencies match these filters.", error: "Could not load agency information.", denied: "Allow location access to select your current region automatically.", call: "Call", site: "Website", map: "Map", distance: "km", language: "Supports selected language", hours: "Hours", verified: "Verified", approximate: "Distances are estimates based on the registered main location.", currentRegion: "Current region" },
  vi: { title: "Tìm cơ quan hỗ trợ phù hợp", description: "Chọn loại hỗ trợ và tìm cơ quan gần vị trí hiện tại.", all: "Tất cả dịch vụ", immigration: "Cư trú", labor: "Lao động & lương", accident: "Tai nạn lao động", interpretation: "Phiên dịch & đời sống", languageOnly: "Chỉ hỗ trợ tiếng Việt", location: "Sắp xếp theo vị trí", locating: "Đang xác định vị trí…", reset: "Xóa vị trí", count: "cơ quan", empty: "Không có cơ quan phù hợp.", error: "Không thể tải thông tin cơ quan.", denied: "Cho phép truy cập vị trí để tự động chọn khu vực hiện tại.", call: "Gọi", site: "Trang web", map: "Bản đồ", distance: "km", language: "Hỗ trợ ngôn ngữ đã chọn", hours: "Giờ làm việc", verified: "Ngày xác minh", approximate: "Khoảng cách là số ước tính theo vị trí đại diện đã đăng ký.", currentRegion: "Khu vực hiện tại" },
} as const;

const services = [
  ["", "all"], ["immigration", "immigration"], ["labor", "labor"],
  ["industrial_accident", "accident"], ["interpretation", "interpretation"],
] as const;

export function AgencyClient({ language }: { language: Language }) {
  const t = copy[language];
  const [serviceType, setServiceType] = useState("");
  const [languageOnly, setLanguageOnly] = useState(false);
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [region, setRegion] = useState<RegionInfo | null>(null);
  const [agencies, setAgencies] = useState<Agency[]>([]);
  const [loading, setLoading] = useState(true);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    try {
      setAgencies(await getAgencies({ serviceType: serviceType || undefined, language: languageOnly ? language : undefined, latitude: location?.latitude, longitude: location?.longitude }));
    } catch { setError(t.error); }
    finally { setLoading(false); }
  }, [language, languageOnly, location, serviceType, t.error]);

  useEffect(() => { void load(); }, [load]);

  function findLocation() {
    if (location) { setLocation(null); setRegion(null); setError(""); return; }
    if (!navigator.geolocation) { setError(t.denied); return; }
    setLocating(true); setError("");
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        setLocation({ latitude: coords.latitude, longitude: coords.longitude });
        setLocating(false);
        try { setRegion(await resolveRegion(coords.latitude, coords.longitude)); } catch { setRegion(null); }
      },
      () => { setError(t.denied); setLocating(false); },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
    );
  }

  return <>
    <section className="page-heading"><div className="content-width"><div className="eyebrow">JEONBUK SUPPORT NETWORK</div><h1>{t.title}</h1><p>{t.description}</p></div></section>
    <section className="content-width agency-search">
      <div className="agency-toolbar">
        <div className="agency-filters" role="group" aria-label="Service type">
          {services.map(([value, label]) => <button className={serviceType === value ? "active" : ""} key={label} onClick={() => setServiceType(value)}>{t[label]}</button>)}
          <button className={languageOnly ? "active" : ""} onClick={() => setLanguageOnly((value) => !value)}><IconGlobe size={16} />{t.languageOnly}</button>
        </div>
        <button className={`location-button ${location ? "active" : ""}`} onClick={findLocation} disabled={locating}><IconPin size={16} />{locating ? t.locating : location ? t.reset : t.location}</button>
      </div>
      {location && <p className="location-note">{region?.name ? <><b>{t.currentRegion}: {region.name[language] || region.name.ko}</b> · </> : null}{t.approximate}</p>}
      {error && <p className="inline-error">{error}</p>}
      <p className="result-meta">{loading ? "…" : `${agencies.length} ${t.count}`}</p>
      {!loading && agencies.length === 0 && <div className="agency-empty">{t.empty}</div>}
      <div className="agency-grid">
        {agencies.map((agency) => <article className="agency-card" key={agency.id}>
          <div className="agency-card-top"><span className={`agency-kind ${agency.emergency ? "urgent" : ""}`}>{agency.emergency ? "24/7" : agency.region.toUpperCase()}</span>{agency.distance_km !== null && <b>{agency.distance_km.toFixed(1)} {t.distance}</b>}</div>
          <h2>{localized(agency.name, language)}</h2><p>{localized(agency.description, language)}</p>
          <dl><div><dt>{t.hours}</dt><dd>{localized(agency.hours, language)}</dd></div><div><dt>{t.language}</dt><dd>{agency.supported_languages.includes(language) ? <IconCheck size={14} /> : "—"}</dd></div><div><dt>{t.verified}</dt><dd>{agency.verified_at}</dd></div></dl>
          <div className="agency-actions"><a href={`tel:${agency.phone}`}>{t.call} {agency.phone}</a><a href={agency.website} target="_blank" rel="noreferrer">{t.site} ↗</a>{agency.latitude !== null && <a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(agency.address)}`} target="_blank" rel="noreferrer">{t.map} ↗</a>}</div>
        </article>)}
      </div>
    </section>
  </>;
}
