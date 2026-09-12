// 문서 검토 UI 전체(업로드·표준 문서 가이드·위험 분석 결과)를 담당하는 파일
"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, DocumentExplanation, RiskItem, explainDocument } from "../lib/api";
import { Language, localized, withLanguage } from "../lib/i18n";
import { IconCheck, IconDocument, IconLock, IconWarning } from "../components/icons";

const copy = {
  ko: { title: "고용·행정 문서 검토", desc: "근로계약서, 임금명세서 등 고용 관련 문서를 업로드하면 문서 내용을 읽고 공식 기준과 비교하여 확인이 필요한 조항을 알려드립니다.", disclaimer: "법적 판단을 확정하는 서비스가 아니며, 문제가 의심되는 항목을 확인하도록 돕는 기능입니다.", ocrBadge: "문서 인식(OCR) 신뢰도", noSourceLink: "상세 출처 링크를 확인할 수 없습니다", choose: "PDF, 이미지 또는 텍스트 파일 선택", consent: "스캔 PDF·이미지는 개인정보를 포함한 원본이 AI 분석을 위해 일시 전송될 수 있음을 확인했습니다.", submit: "문서 검토하기", summary: "쉬운 설명", points: "핵심 내용", terms: "계약 내용 요약", risks: "확인이 필요한 항목", deviations: "공식 기준과 다른 내용", basis: "근거", actions: "내가 해야 할 일", deadlines: "확인된 기한", cautions: "주의사항", guides: "관련 가이드", again: "다른 문서 확인", redacted: "텍스트 개인정보가 자동 마스킹되었습니다.", docType: { employment_contract: "근로계약서", payslip: "급여명세서", resignation_document: "퇴직 관련 서류", administrative_notice: "행정 안내문", unknown: "일반 문서" }, termLabels: { wage: "임금", working_hours: "근로시간", break_time: "휴게시간", contract_period: "계약기간", holiday: "휴일", pay_day: "임금 지급일" }, levelLabels: { SAFE: "확인됨", CHECK: "확인 필요", WARNING: "주의" } },
  en: { title: "Employment & administrative document review", desc: "Upload an employment document such as a contract or payslip; we read it and compare clauses against official standards, flagging items to check.", disclaimer: "This service does not make legal determinations — it helps you identify items that may need checking.", ocrBadge: "OCR confidence", noSourceLink: "Detailed source link unavailable", choose: "Choose a PDF, image, or text file", consent: "I understand that scanned PDFs or images may be sent temporarily for AI analysis with personal data visible.", submit: "Review document", summary: "Plain summary", points: "Key points", terms: "Contract summary", risks: "Items to check", deviations: "Differences from official standards", basis: "Basis", actions: "What to do", deadlines: "Deadlines found", cautions: "Cautions", guides: "Related guides", again: "Check another document", redacted: "Personal data in extracted text was redacted.", docType: { employment_contract: "Employment contract", payslip: "Payslip", resignation_document: "Resignation document", administrative_notice: "Administrative notice", unknown: "General document" }, termLabels: { wage: "Wage", working_hours: "Working hours", break_time: "Break time", contract_period: "Contract period", holiday: "Holidays", pay_day: "Pay day" }, levelLabels: { SAFE: "Confirmed", CHECK: "Needs check", WARNING: "Caution" } },
  vi: { title: "Kiểm tra tài liệu lao động & hành chính", desc: "Tải lên hợp đồng lao động, phiếu lương... — chúng tôi đọc nội dung và so sánh với tiêu chuẩn chính thức để chỉ ra các điều khoản cần kiểm tra.", disclaimer: "Dịch vụ này không đưa ra kết luận pháp lý — chỉ giúp bạn nhận biết các mục cần kiểm tra.", ocrBadge: "Độ tin cậy OCR", noSourceLink: "Không có liên kết chi tiết đến nguồn", choose: "Chọn PDF, ảnh hoặc tệp văn bản", consent: "Tôi hiểu rằng PDF quét hoặc ảnh có thể được gửi tạm thời để AI phân tích khi còn hiển thị dữ liệu cá nhân.", submit: "Kiểm tra tài liệu", summary: "Giải thích dễ hiểu", points: "Nội dung chính", terms: "Tóm tắt hợp đồng", risks: "Mục cần kiểm tra", deviations: "Khác với tiêu chuẩn chính thức", basis: "Căn cứ", actions: "Việc cần làm", deadlines: "Thời hạn", cautions: "Lưu ý", guides: "Hướng dẫn liên quan", again: "Xem tài liệu khác", redacted: "Dữ liệu cá nhân trong văn bản đã được che.", docType: { employment_contract: "Hợp đồng lao động", payslip: "Phiếu lương", resignation_document: "Giấy tờ thôi việc", administrative_notice: "Thông báo hành chính", unknown: "Tài liệu chung" }, termLabels: { wage: "Tiền lương", working_hours: "Giờ làm việc", break_time: "Giờ nghỉ", contract_period: "Thời hạn hợp đồng", holiday: "Ngày nghỉ", pay_day: "Ngày trả lương" }, levelLabels: { SAFE: "Đã xác nhận", CHECK: "Cần kiểm tra", WARNING: "Chú ý" } },
} as const;

const standardDocs = {
  ko: {
    heading: "표준 문서와 작성 방법", intro: "정상적인 문서가 어떤 형태인지 미리 확인하세요.",
    items: [
      { title: "표준 근로계약서 체크리스트", purpose: "근로계약을 맺을 때 서면으로 반드시 확인해야 하는 항목입니다.", checklist: ["근로계약기간", "근무장소", "업무내용", "근로시간", "휴게시간", "임금", "임금 지급일", "휴일", "연차"], source: { label: "고용노동부 표준근로계약서", url: "https://www.moel.go.kr/" } },
      { title: "임금명세서 확인 가이드", purpose: "매달 받는 급여명세서에서 확인할 항목입니다.", checklist: ["기본급과 소정근로시간", "연장·야간·휴일근로 수당", "공제 항목과 금액의 근거", "실지급액과 지급일"], source: { label: "고용노동부 임금명세서 안내", url: "https://www.moel.go.kr/" } },
      { title: "계약 전 확인할 사항", purpose: "외국인 근로자가 서명하기 전에 확인할 내용입니다.", checklist: ["이해되지 않는 조항은 서명 전에 질문", "구두 약속은 서면으로 기록", "계약서 사본을 반드시 보관", "위약금·손해배상 조항 확인"], source: { label: "고용노동부 외국인 근로자 안내", url: "https://www.moel.go.kr/" } },
    ],
  },
  en: {
    heading: "Standard documents & how to write them", intro: "See what a proper document should look like before you sign.",
    items: [
      { title: "Standard employment contract checklist", purpose: "Items that must be confirmed in writing when signing a contract.", checklist: ["Contract period", "Workplace", "Job duties", "Working hours", "Break time", "Wage", "Pay day", "Holidays", "Annual leave"], source: { label: "MOEL standard employment contract", url: "https://www.moel.go.kr/" } },
      { title: "Payslip check guide", purpose: "What to check on your monthly payslip.", checklist: ["Base pay and contractual hours", "Overtime, night, and holiday premiums", "Deduction items and their basis", "Net pay and pay date"], source: { label: "MOEL payslip guidance", url: "https://www.moel.go.kr/" } },
      { title: "Before signing a contract", purpose: "What foreign workers should confirm before signing.", checklist: ["Ask about any clause you do not understand", "Put verbal promises in writing", "Keep a copy of the contract", "Check penalty and damages clauses"], source: { label: "MOEL guidance for foreign workers", url: "https://www.moel.go.kr/" } },
    ],
  },
  vi: {
    heading: "Tài liệu chuẩn & cách soạn thảo", intro: "Xem trước tài liệu đúng chuẩn trông như thế nào trước khi ký.",
    items: [
      { title: "Danh sách kiểm tra hợp đồng lao động chuẩn", purpose: "Các mục phải được xác nhận bằng văn bản khi ký hợp đồng.", checklist: ["Thời hạn hợp đồng", "Nơi làm việc", "Nội dung công việc", "Giờ làm việc", "Giờ nghỉ", "Tiền lương", "Ngày trả lương", "Ngày nghỉ", "Nghỉ phép năm"], source: { label: "Hợp đồng lao động chuẩn của MOEL", url: "https://www.moel.go.kr/" } },
      { title: "Hướng dẫn kiểm tra phiếu lương", purpose: "Những gì cần kiểm tra trên phiếu lương hàng tháng.", checklist: ["Lương cơ bản và giờ làm theo hợp đồng", "Phụ cấp tăng ca, làm đêm, ngày nghỉ", "Các khoản khấu trừ và căn cứ", "Số tiền thực nhận và ngày trả"], source: { label: "Hướng dẫn phiếu lương của MOEL", url: "https://www.moel.go.kr/" } },
      { title: "Trước khi ký hợp đồng", purpose: "Người lao động nước ngoài cần xác nhận trước khi ký.", checklist: ["Hỏi về điều khoản chưa hiểu", "Ghi lại lời hứa miệng bằng văn bản", "Giữ một bản sao hợp đồng", "Kiểm tra điều khoản phạt và bồi thường"], source: { label: "Hướng dẫn của MOEL cho lao động nước ngoài", url: "https://www.moel.go.kr/" } },
    ],
  },
} as const;

const sectionLabels = {
  ko: { clause: "문제가 되는 조항", standard: "공식 기준", problem: "문제점", impact: "사용자에게 미치는 영향", revision: "권장 수정", checks: "확인할 것", detected: "계약서 값", official: "공식 기준 값", difference: "차이" },
  en: { clause: "Clause in question", standard: "Official standard", problem: "Problem", impact: "Impact on you", revision: "Recommended revision", checks: "What to check", detected: "In contract", official: "Official", difference: "Difference" },
  vi: { clause: "Điều khoản có vấn đề", standard: "Tiêu chuẩn chính thức", problem: "Vấn đề", impact: "Ảnh hưởng đến bạn", revision: "Sửa đổi đề xuất", checks: "Cần kiểm tra", detected: "Trong hợp đồng", official: "Chính thức", difference: "Chênh lệch" },
} as const;

function RiskCard({ item, t, s }: { item: RiskItem; t: (typeof copy)[Language]; s: (typeof sectionLabels)[Language] }) {
  const detailed = item.problem || item.official_standard;
  return (
    <div className={`risk-card ${item.level.toLowerCase()}`}>
      <div className={`risk-head ${item.level.toLowerCase()}`}><span className={`risk-badge ${item.level.toLowerCase()}`}>{item.level === "SAFE" ? <IconCheck size={13} /> : <IconWarning size={13} />}{t.levelLabels[item.level]}</span>{item.title && <b>{item.title}</b>}</div>
      <div className="risk-section"><b>{s.clause}</b><blockquote>{item.clause}</blockquote></div>
      {item.official_standard && <div className="risk-section"><b>{s.standard}</b><p>{item.official_standard}</p></div>}
      {(item.detected_value || item.official_value) && <div className="risk-compare">{item.detected_value && <span><small>{s.detected}</small><b>{item.detected_value}</b></span>}{item.official_value && <span><small>{s.official}</small><b>{item.official_value}</b></span>}{item.difference && <span className="diff"><small>{s.difference}</small><b>{item.difference}</b></span>}</div>}
      <div className="risk-section"><b>{s.problem}</b><p>{detailed ? item.problem : item.reason}</p></div>
      {item.impact && <div className="risk-section"><b>{s.impact}</b><p>{item.impact}</p></div>}
      {item.recommended_revision && <div className="risk-section"><b>{s.revision}</b><p>{item.recommended_revision}</p></div>}
      {!detailed && <p><b>{item.recommendation}</b></p>}
      {item.checks.length > 0 && <div className="risk-section"><b>{s.checks}</b><ol>{item.checks.map((check) => <li key={check}>{check}</li>)}</ol></div>}
      {item.sources.length > 0 && <div className="risk-sources"><b>{t.basis}:</b>{item.sources.map((source) => <span className="risk-source-entry" key={source.chunk_id}>
        {source.url_specific
          ? <a href={source.url} target="_blank" rel="noopener noreferrer">{source.title}{source.display_title ? ` — ${source.display_title}` : ""} ({source.publisher}{source.display_publisher ? ` · ${source.display_publisher}` : ""}) ↗</a>
          : <span className="source-disabled-inline">{source.title}{source.display_title ? ` — ${source.display_title}` : ""} ({source.publisher}{source.display_publisher ? ` · ${source.display_publisher}` : ""}) · {t.noSourceLink}</span>}
        {source.source_summary && <small className="source-summary">{source.source_summary}</small>}
      </span>)}</div>}
    </div>
  );
}

export function DocumentClient({ language }: { language: Language }) {
  const t = copy[language];
  const s = standardDocs[language];
  const [file, setFile] = useState<File | null>(null); const [consent, setConsent] = useState(false); const [result, setResult] = useState<DocumentExplanation | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const needsConsent = !!file && file.type !== "text/plain";
  const errorByStatus: Record<number, Record<Language, string>> = {
    400: { ko: "파일을 읽을 수 없습니다. 파일 형식(PDF·PNG·JPG·WEBP·TXT)과 크기(최대 5MB)를 확인해 주세요.", en: "The file could not be read. Check the format (PDF, PNG, JPG, WEBP, TXT) and size (max 5MB).", vi: "Không đọc được tệp. Kiểm tra định dạng (PDF, PNG, JPG, WEBP, TXT) và dung lượng (tối đa 5MB)." },
    422: { ko: "스캔 문서·이미지는 아래 동의 항목에 체크해야 분석할 수 있습니다.", en: "Scanned documents and images require the consent checkbox below.", vi: "Tài liệu quét và ảnh cần đánh dấu ô đồng ý bên dưới." },
    429: { ko: "요청이 많습니다. 잠시 후 다시 시도해 주세요.", en: "Too many requests. Please try again shortly.", vi: "Quá nhiều yêu cầu. Vui lòng thử lại sau." },
    503: { ko: "AI 분석 서비스를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.", en: "The AI analysis service is unavailable. Please try again later.", vi: "Dịch vụ phân tích AI hiện không khả dụng. Vui lòng thử lại sau." },
  };
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || (needsConsent && !consent)) return;
    setLoading(true); setError("");
    try {
      setResult(await explainDocument(file, language, consent));
    } catch (requestError) {
      if (requestError instanceof ApiError && errorByStatus[requestError.status]) {
        let detail = "";
        try { detail = JSON.parse(requestError.message).detail ?? ""; } catch { detail = ""; }
        setError(`${errorByStatus[requestError.status][language]}${detail ? ` (${detail})` : ""}`);
      } else {
        setError({ ko: "문서를 처리할 수 없습니다. 연결 상태를 확인해 주세요.", en: "Unable to process the document. Please check your connection.", vi: "Không thể xử lý tài liệu. Vui lòng kiểm tra kết nối." }[language]);
      }
    } finally { setLoading(false); }
  }
  const typeLabel = result ? (t.docType[result.document_type as keyof typeof t.docType] ?? t.docType.unknown) : "";
  return <section className="document-shell content-width">
    <header className="document-heading"><div className="eyebrow">DOCUMENT REVIEW</div><h1>{t.title}</h1><p>{t.desc}</p><p className="document-disclaimer"><IconWarning size={14} /><b>{t.disclaimer}</b></p></header>
    {!result ? <>
      <form className="document-upload" onSubmit={submit}>
        <label className="file-drop"><input type="file" accept=".pdf,.txt,image/png,image/jpeg,image/webp" onChange={(event) => { setFile(event.target.files?.[0] || null); setConsent(false); }} /><span><IconDocument size={38} /></span><strong>{file?.name || t.choose}</strong><small>PDF · PNG · JPG · WEBP · TXT · max 5MB</small></label>
        {needsConsent && <label className="consent"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} /><span>{t.consent}</span></label>}
        {error && <p className="inline-error">{error}</p>}
        <button className="primary chat-submit" disabled={!file || loading || (needsConsent && !consent)}>{loading ? "…" : t.submit}</button>
      </form>
      <section className="standard-docs">
        <h2>{s.heading}</h2>
        <p>{s.intro}</p>
        <div className="standard-grid">
          {s.items.map((item) => <article className="standard-card" key={item.title}>
            <h3>{item.title}</h3>
            <p>{item.purpose}</p>
            <ul>{item.checklist.map((entry) => <li key={entry}><IconCheck size={14} />{entry}</li>)}</ul>
            <a href={item.source.url} target="_blank" rel="noreferrer"><b>{item.source.label} ↗</b></a>
          </article>)}
        </div>
      </section>
    </> : <div className="document-results">
      <div className="doc-badges"><span className="doc-type-badge"><IconDocument size={16} />{typeLabel}</span>{result.ocr_used && result.ocr_confidence !== null && <span className="doc-type-badge">{t.ocrBadge} {(result.ocr_confidence * 100).toFixed(0)}%</span>}</div>
      {result.privacy_redacted && <div className="privacy-note"><IconLock size={15} />{t.redacted}</div>}
      <ResultSection title={t.summary} items={[result.summary]} />
      {Object.keys(result.key_terms).length > 0 && <section className="document-result-card"><h2>{t.terms}</h2><dl className="term-list">{Object.entries(result.key_terms).map(([term, clause]) => <div key={term}><dt>{t.termLabels[term as keyof typeof t.termLabels] ?? term}</dt><dd>{clause}</dd></div>)}</dl></section>}
      {result.risk_items.some((item) => item.level !== "SAFE") && <section className="document-result-card deviation-summary"><h2><IconWarning size={17} />{t.deviations}</h2><ul>{result.risk_items.filter((item) => item.level !== "SAFE").map((item) => <li key={(item.title || item.clause) + item.level}><span className={`risk-badge inline ${item.level.toLowerCase()}`}>{t.levelLabels[item.level]}</span><b>{item.title || item.clause.slice(0, 40)}</b>{item.difference ? ` · ${item.difference}` : ""}</li>)}</ul></section>}
      {result.risk_items.length > 0 && <section className="document-result-card"><h2>{t.risks}</h2><div className="risk-list">{result.risk_items.map((item) => <RiskCard item={item} t={t} s={sectionLabels[language]} key={item.clause + item.level} />)}</div></section>}
      <ResultSection title={t.points} items={result.key_points} />
      <ResultSection title={t.actions} items={result.actions} numbered />
      <ResultSection title={t.deadlines} items={result.deadlines} />
      <ResultSection title={t.cautions} items={result.cautions} caution />
      {result.related_guides.length > 0 && <section className="document-result-card"><h2>{t.guides}</h2>{result.related_guides.map((guide) => <Link className="document-guide" href={withLanguage(`/guides/${guide.id}`, language)} key={guide.id}>{localized(guide.title, language)} <b>→</b></Link>)}</section>}
      <button className="secondary reset-button" onClick={() => { setResult(null); setFile(null); }}>{t.again}</button>
    </div>}
  </section>;
}

function ResultSection({ title, items, numbered, caution }: { title: string; items: string[]; numbered?: boolean; caution?: boolean }) { if (!items.length) return null; const List = numbered ? "ol" : "ul"; return <section className={`document-result-card ${caution ? "caution" : ""}`}><h2>{title}</h2><List>{items.map((item) => <li key={item}>{item}</li>)}</List></section>; }
