"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { DocumentExplanation, RiskItem, explainDocument } from "../lib/api";
import { Language, localized, withLanguage } from "../lib/i18n";
import { IconCheck, IconDocument, IconLock, IconWarning } from "../components/icons";

const copy = {
  ko: { title: "고용·행정 문서 검토", desc: "문서를 업로드하면 핵심 내용을 정리하고, 확인이 필요한 조항을 공식 자료와 비교해 안내해 드려요.", choose: "PDF, 이미지 또는 텍스트 파일 선택", consent: "스캔 PDF·이미지는 개인정보를 포함한 원본이 AI 분석을 위해 일시 전송될 수 있음을 확인했습니다.", submit: "문서 검토하기", summary: "쉬운 설명", points: "핵심 내용", terms: "주요 조건", risks: "확인이 필요한 항목", basis: "근거", actions: "내가 해야 할 일", deadlines: "확인된 기한", cautions: "주의사항", guides: "관련 가이드", again: "다른 문서 확인", redacted: "텍스트 개인정보가 자동 마스킹되었습니다.", docType: { employment_contract: "근로계약서", payslip: "급여명세서", resignation_document: "퇴직 관련 서류", administrative_notice: "행정 안내문", unknown: "일반 문서" }, termLabels: { wage: "임금", working_hours: "근로시간", break_time: "휴게시간", contract_period: "계약기간", holiday: "휴일", pay_day: "임금 지급일" }, levelLabels: { SAFE: "확인됨", CHECK: "확인 필요", WARNING: "주의" } },
  en: { title: "Employment & administrative document review", desc: "Upload a document to get a plain summary and clauses compared against official standards.", choose: "Choose a PDF, image, or text file", consent: "I understand that scanned PDFs or images may be sent temporarily for AI analysis with personal data visible.", submit: "Review document", summary: "Plain summary", points: "Key points", terms: "Key terms", risks: "Items to check", basis: "Basis", actions: "What to do", deadlines: "Deadlines found", cautions: "Cautions", guides: "Related guides", again: "Check another document", redacted: "Personal data in extracted text was redacted.", docType: { employment_contract: "Employment contract", payslip: "Payslip", resignation_document: "Resignation document", administrative_notice: "Administrative notice", unknown: "General document" }, termLabels: { wage: "Wage", working_hours: "Working hours", break_time: "Break time", contract_period: "Contract period", holiday: "Holidays", pay_day: "Pay day" }, levelLabels: { SAFE: "Confirmed", CHECK: "Needs check", WARNING: "Caution" } },
  vi: { title: "Kiểm tra tài liệu lao động & hành chính", desc: "Tải tài liệu lên để nhận tóm tắt dễ hiểu và các điều khoản được so sánh với tiêu chuẩn chính thức.", choose: "Chọn PDF, ảnh hoặc tệp văn bản", consent: "Tôi hiểu rằng PDF quét hoặc ảnh có thể được gửi tạm thời để AI phân tích khi còn hiển thị dữ liệu cá nhân.", submit: "Kiểm tra tài liệu", summary: "Giải thích dễ hiểu", points: "Nội dung chính", terms: "Điều khoản chính", risks: "Mục cần kiểm tra", basis: "Căn cứ", actions: "Việc cần làm", deadlines: "Thời hạn", cautions: "Lưu ý", guides: "Hướng dẫn liên quan", again: "Xem tài liệu khác", redacted: "Dữ liệu cá nhân trong văn bản đã được che.", docType: { employment_contract: "Hợp đồng lao động", payslip: "Phiếu lương", resignation_document: "Giấy tờ thôi việc", administrative_notice: "Thông báo hành chính", unknown: "Tài liệu chung" }, termLabels: { wage: "Tiền lương", working_hours: "Giờ làm việc", break_time: "Giờ nghỉ", contract_period: "Thời hạn hợp đồng", holiday: "Ngày nghỉ", pay_day: "Ngày trả lương" }, levelLabels: { SAFE: "Đã xác nhận", CHECK: "Cần kiểm tra", WARNING: "Chú ý" } },
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

function RiskCard({ item, t }: { item: RiskItem; t: (typeof copy)[Language] }) {
  return (
    <div className={`risk-card ${item.level.toLowerCase()}`}>
      <div className="risk-head"><span className={`risk-badge ${item.level.toLowerCase()}`}>{item.level === "SAFE" ? <IconCheck size={13} /> : <IconWarning size={13} />}{t.levelLabels[item.level]}</span></div>
      <blockquote>{item.clause}</blockquote>
      <p>{item.reason}</p>
      <p><b>{item.recommendation}</b></p>
      {item.checks.length > 0 && <ol>{item.checks.map((check) => <li key={check}>{check}</li>)}</ol>}
      {item.sources.length > 0 && <div className="risk-sources"><b>{t.basis}:</b> {item.sources.map((source) => <a key={source.chunk_id} href={source.url} target="_blank" rel="noreferrer">{source.title} ({source.publisher}) ↗</a>)}</div>}
    </div>
  );
}

export function DocumentClient({ language }: { language: Language }) {
  const t = copy[language];
  const s = standardDocs[language];
  const [file, setFile] = useState<File | null>(null); const [consent, setConsent] = useState(false); const [result, setResult] = useState<DocumentExplanation | null>(null); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  const needsConsent = !!file && file.type !== "text/plain";
  async function submit(event: FormEvent) { event.preventDefault(); if (!file || (needsConsent && !consent)) return; setLoading(true); setError(""); try { setResult(await explainDocument(file, language, consent)); } catch { setError("문서를 처리할 수 없습니다. 파일과 API 설정을 확인해 주세요. / Unable to process the document."); } finally { setLoading(false); } }
  const typeLabel = result ? (t.docType[result.document_type as keyof typeof t.docType] ?? t.docType.unknown) : "";
  return <section className="document-shell content-width">
    <header className="document-heading"><div className="eyebrow">DOCUMENT REVIEW</div><h1>{t.title}</h1><p>{t.desc}</p></header>
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
      <div className="doc-type-badge"><IconDocument size={16} />{typeLabel}</div>
      {result.privacy_redacted && <div className="privacy-note"><IconLock size={15} />{t.redacted}</div>}
      <ResultSection title={t.summary} items={[result.summary]} />
      {Object.keys(result.key_terms).length > 0 && <section className="document-result-card"><h2>{t.terms}</h2><dl className="term-list">{Object.entries(result.key_terms).map(([term, clause]) => <div key={term}><dt>{t.termLabels[term as keyof typeof t.termLabels] ?? term}</dt><dd>{clause}</dd></div>)}</dl></section>}
      {result.risk_items.length > 0 && <section className="document-result-card"><h2>{t.risks}</h2><div className="risk-list">{result.risk_items.map((item) => <RiskCard item={item} t={t} key={item.clause + item.level} />)}</div></section>}
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
