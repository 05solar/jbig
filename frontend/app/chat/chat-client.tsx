// AI 상담 챗봇 UI 전체(대화·출처 카드·위치·피드백)를 담당하는 파일
"use client";

import Link from "next/link";
import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ApiError, ConsultationResponse, createConsultation, Guide, resolveRegion, sendFeedback } from "../lib/api";
import { Language, localized, messages, withLanguage } from "../lib/i18n";
import { IconCheck, IconChevronDown, IconLock, IconPhone, IconPin, IconPlus, IconSend, IconSpark, IconThumbDown, IconThumbUp, IconUser, IconWarning } from "../components/icons";

type Turn = { id: string; question: string; answer: ConsultationResponse };

const contextCopy = {
  ko: { userType: "사용자 유형 (선택)", worker: "외국인 근로자", student: "유학생", region: "지역 (예: 전주)", location: "위치", locationHint: "위치 권한을 허용하면 현재 지역을 자동으로 선택할 수 있습니다.", viewingGuide: "현재 보고 있는 가이드", tooMany: "요청이 많습니다. 잠시 후 다시 시도해 주세요.", connectError: "연결할 수 없습니다. 연결 상태를 확인해 주세요.", feedbackError: "의견을 전송하지 못했습니다." },
  en: { userType: "User type (optional)", worker: "Foreign worker", student: "Student", region: "Region (e.g. Jeonju)", location: "Location", locationHint: "Allow location access to select your current region automatically.", viewingGuide: "Guide you are viewing", tooMany: "Too many requests. Please try again shortly.", connectError: "Unable to connect. Please check your connection.", feedbackError: "Unable to send feedback." },
  vi: { userType: "Loại người dùng (tùy chọn)", worker: "Người lao động", student: "Du học sinh", region: "Khu vực (VD: Jeonju)", location: "Vị trí", locationHint: "Cho phép truy cập vị trí để tự động chọn khu vực hiện tại.", viewingGuide: "Hướng dẫn đang xem", tooMany: "Quá nhiều yêu cầu. Vui lòng thử lại sau.", connectError: "Không thể kết nối. Vui lòng kiểm tra kết nối.", feedbackError: "Không gửi được phản hồi." },
} as const;

const guideQuestionTemplates = {
  ko: (title: string) => [`제 상황도 ${title}에 해당하나요?`, "어떤 자료를 준비해야 하나요?", "어디에 신청하거나 신고해야 하나요?"],
  en: (title: string) => [`Does my situation count as "${title}"?`, "What documents should I prepare?", "Where should I apply or report?"],
  vi: (title: string) => [`Trường hợp của tôi có thuộc "${title}" không?`, "Tôi cần chuẩn bị giấy tờ gì?", "Tôi nên nộp hoặc khai báo ở đâu?"],
} as const;

function answerLabel(answer: ConsultationResponse, language: Language) {
  const t = messages[language];
  if (answer.answer_mode === "rag") return t.rag;
  if (answer.answer_mode === "insufficient_evidence") return t.insufficient;
  if (answer.answer_mode === "ai") return t.aiAnswer;
  return t.rulesAnswer;
}

function trustLabel(level: "high" | "medium" | "low", language: Language) {
  const labels = { ko: ["신뢰도 높음", "검토 필요", "주의"], en: ["High trust", "Review needed", "Caution"], vi: ["Độ tin cậy cao", "Cần kiểm tra", "Lưu ý"] }[language];
  return labels[level === "high" ? 0 : level === "medium" ? 1 : 2];
}

function sourceDateLabel(source: ConsultationResponse["sources"][number], language: Language) {
  const labels = { ko: ["발행일", "등록일"], en: ["Published", "Added"], vi: ["Ban hành", "Đăng ký"] }[language];
  const date = source.published_at || source.collected_at;
  return date ? `${labels[source.published_at ? 0 : 1]} ${date.slice(0, 10)}` : "";
}

function sourceFreshnessLabel(source: ConsultationResponse["sources"][number], language: Language) {
  if (source.freshness_type === "live_verification_required") return { ko: "실시간 확인 필요", en: "Live confirmation required", vi: "Cần xác nhận trực tiếp" }[language];
  if (source.freshness_status !== "최신 공식자료 확인 완료") return source.freshness_status;
  return "";
}

function CustomSelect({ value, options, onChange, ariaLabel }: { value: string; options: { value: string; label: string }[]; onChange: (value: string) => void; ariaLabel: string }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onOutsideClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onOutsideClick);
    return () => document.removeEventListener("mousedown", onOutsideClick);
  }, []);

  const selected = options.find((option) => option.value === value) ?? options[0];
  return (
    <div className={`custom-select ${open ? "open" : ""}`} ref={rootRef}>
      <button type="button" className="custom-select-trigger" aria-label={ariaLabel} aria-expanded={open} onClick={() => setOpen((state) => !state)}>
        {selected.label}
        <IconChevronDown size={16} />
      </button>
      {open && (
        <ul className="custom-select-menu" role="listbox">
          {options.map((option) => (
            <li key={option.value} role="option" aria-selected={option.value === value} className={option.value === value ? "selected" : ""} onClick={() => { onChange(option.value); setOpen(false); }}>
              {option.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AssistantAnswer({ answer, language, onFeedback, feedbackSent }: { answer: ConsultationResponse; language: Language; onFeedback: (rating: "helpful" | "not_helpful") => void; feedbackSent: boolean }) {
  const t = messages[language];
  return <div className="assistant-content">
    <div className="assistant-label"><span className={`answer-label ${answer.answer_mode}`}>{answerLabel(answer, language)}</span>{answer.cached ? ` · ${t.cachedAnswer}` : ""}</div>
    <p className="generated-answer">{answer.message}</p>
    {answer.answer_mode === "insufficient_evidence" && <div className="urgent-notice"><IconWarning size={18} />{t.insufficient}</div>}
    {answer.evidence_sufficient && <div className="privacy-note"><IconCheck size={16} />{t.evidenceNote}</div>}
    {answer.urgent_notice && <div className="urgent-notice"><IconWarning size={18} />{answer.urgent_notice}</div>}
    {answer.sources.length > 0 && <section className="chat-extra"><h3>{t.sourceDocuments}</h3><div className="source-list">{answer.sources.map((source) => {
      const body = <><strong>{source.title}<b className={`trust-badge ${source.trust_level}`}>{trustLabel(source.trust_level, language)}</b></strong>{language !== "ko" && source.display_title && <span className="source-translated-title">{source.display_title}</span>}<span>{source.publisher}{language !== "ko" && source.display_publisher ? ` · ${source.display_publisher}` : ""} · {language === "ko" ? "관련도" : language === "en" ? "Relevance" : "Mức liên quan"} <b>{(source.relevance * 100).toFixed(0)}%</b> · {language === "ko" ? "권위" : language === "en" ? "Authority" : "Thẩm quyền"} <b>{(source.authority_score * 100).toFixed(0)}%</b></span>{language !== "ko" && source.source_summary && <span className="source-summary">{source.source_summary}</span>}<small>{sourceDateLabel(source, language)}{source.last_checked_at ? ` · ${language === "ko" ? "마지막 확인" : language === "en" ? "Checked" : "Kiểm tra"} ${source.last_checked_at.slice(0, 10)}` : ""}{sourceFreshnessLabel(source, language) ? ` · ${sourceFreshnessLabel(source, language)}` : ""}</small></>;
      return source.url_specific
        ? <a href={source.url} target="_blank" rel="noopener noreferrer" key={source.chunk_id}>{body}</a>
        : <div className="source-disabled" key={source.chunk_id}>{body}<small className="no-link-note">{{ ko: "상세 출처 링크를 확인할 수 없습니다.", en: "Detailed source link unavailable.", vi: "Không có liên kết chi tiết đến nguồn." }[language]}</small></div>;
    })}</div></section>}
    {answer.guides.length > 0 && <section className="chat-extra"><h3>{t.relatedGuide}</h3><div className="chat-guide-list">{answer.guides.map((guide) => <Link href={withLanguage(`/guides/${guide.id}`, language)} key={guide.id}><span className={`category-badge ${guide.category}`}>{guide.category === "residency" ? t.residency : t.labor}</span><strong>{localized(guide.title, language)}</strong><small>{localized(guide.summary, language)}</small></Link>)}</div></section>}
    {answer.follow_up_questions.length > 0 && <section className="chat-extra"><h3>{t.followUp}</h3><ul>{answer.follow_up_questions.map((item) => <li key={item}>{item}</li>)}</ul></section>}
    {answer.agencies.length > 0 && <section className="chat-extra"><h3>{t.help}</h3><div className="answer-agencies">{answer.agencies.map((agency) => <div key={agency.id}><strong>{localized(agency.name, language)}</strong><a href={`tel:${agency.phone}`}><IconPhone size={15} />{agency.phone}{agency.distance_km !== null ? ` · ${agency.distance_km} km` : ""}</a></div>)}</div></section>}
    <div className="chat-feedback">{feedbackSent ? <span>{t.feedbackThanks}</span> : <><span>{t.feedbackQuestion}</span><button onClick={() => onFeedback("helpful")}><IconThumbUp size={15} />{t.helpful}</button><button onClick={() => onFeedback("not_helpful")}><IconThumbDown size={15} />{t.notHelpful}</button></>}</div>
  </div>;
}

export function ChatClient({ language, guide = null }: { language: Language; guide?: Guide | null }) {
  const t = messages[language];
  const c = contextCopy[language];
  const guideTitle = guide ? localized(guide.title, language) : "";
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [userType, setUserType] = useState("");
  const [region, setRegion] = useState("");
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const lastAnswerRef = useRef<HTMLDivElement>(null);

  // While waiting, keep the typing indicator visible at the bottom; once the
  // answer arrives, jump to the TOP of the new answer so reading starts there.
  useEffect(() => { if (loading) endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [loading]);
  useEffect(() => { lastAnswerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }); }, [turns]);

  async function send() {
    const text = question.trim();
    if (text.length < 2 || loading) return;
    setQuestion(""); setLoading(true); setError(""); setFeedbackSent(false);
    try {
      const guideContext = guideTitle ? `${c.viewingGuide}: ${guideTitle}` : "";
      const conversation_context = [guideContext, ...turns.slice(-3).map((turn) => turn.question)].filter(Boolean).join("\n").slice(-2200) || undefined;
      const answer = await createConsultation(text, language, { user_type: userType || undefined, region: region || undefined, conversation_context, ...location });
      setTurns((previous) => [...previous, { id: answer.consultation_id || `${Date.now()}`, question: text, answer }]);
    } catch (requestError) {
      setQuestion(text);
      setError(requestError instanceof ApiError && requestError.status === 429 ? c.tooMany : c.connectError);
    } finally { setLoading(false); }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void send();
  }

  // Windows/한글 IME: 조합 중 Enter는 keydown이 isComposing(keyCode 229)로
  // 들어와 무시되면 전송이 안 되는 것처럼 보인다. Enter는 항상 개행을 막고,
  // 조합 중이었다면 compositionend 시점에 전송을 이어서 수행한다.
  const composingEnterRef = useRef(false);
  function onComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    if (event.nativeEvent.isComposing || event.keyCode === 229) {
      composingEnterRef.current = true;
      return;
    }
    void send();
  }
  function onComposerCompositionEnd() {
    if (composingEnterRef.current) {
      composingEnterRef.current = false;
      void send();
    }
  }

  function reset() { setQuestion(""); setTurns([]); setError(""); setFeedbackSent(false); }
  function useLocation() {
    if (!navigator.geolocation) { setError(c.locationHint); return; }
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        setLocation({ latitude: coords.latitude, longitude: coords.longitude });
        try {
          const resolved = await resolveRegion(coords.latitude, coords.longitude);
          if (resolved.name) setRegion(resolved.name[language] || resolved.name.ko);
        } catch { /* manual region input stays available */ }
      },
      () => setError(c.locationHint),
    );
  }
  async function feedback(rating: "helpful" | "not_helpful") { const answer = turns.at(-1)?.answer; if (!answer?.consultation_id || feedbackSent) return; try { await sendFeedback(answer.consultation_id, rating); setFeedbackSent(true); } catch { setError(c.feedbackError); } }

  return <section className="chat-shell chatbot-shell content-width">
    <div className="chat-heading"><div className="eyebrow">JBIG CONSULTATION</div><h1>{t.chatTitle}</h1></div>
    <div className="chat-window">
      {turns.length === 0 && <div className="chat-welcome">
        <span className="chat-avatar"><IconSpark size={26} /></span>
        <h2>{language === "ko" ? "안녕하세요. 무엇을 도와드릴까요?" : language === "en" ? "Hello. How can I help?" : "Xin chào. Tôi có thể giúp gì?"}</h2>
        {guide && <div className="guide-context-banner"><span className={`category-badge ${guide.category}`}>{guide.category === "residency" ? t.residency : t.labor}</span><b>{c.viewingGuide}: {guideTitle}</b></div>}
        <div className="suggestion-list">
          {guide ? guideQuestionTemplates[language](guideTitle).map((suggestion) => (
            <button key={suggestion} onClick={() => setQuestion(suggestion)}>{suggestion}</button>
          )) : <>
            <button onClick={() => setQuestion(t.chatPlaceholder.replace("예: ", ""))}>{t.chatPlaceholder}</button>
            <button onClick={() => setQuestion(language === "ko" ? "임금체불이 발생했는데 어떻게 해야 하나요?" : language === "en" ? "What should I do about unpaid wages?" : "Tôi nên làm gì khi bị nợ lương?")}>{language === "ko" ? "임금체불 도움받기" : language === "en" ? "Get help with unpaid wages" : "Hỗ trợ khi bị nợ lương"}</button>
          </>}
        </div>
      </div>}
      {turns.map((turn, index) => <div className="chat-turn" key={turn.id}><div className="message-row user-row"><span className="message-avatar user-avatar"><IconUser size={17} /></span><div className="message-bubble user-bubble"><p>{turn.question}</p></div></div><div className="message-row assistant-row" ref={index === turns.length - 1 ? lastAnswerRef : undefined}><span className="message-avatar assistant-avatar"><IconSpark size={17} /></span><div className="message-bubble assistant-bubble"><AssistantAnswer answer={turn.answer} language={language} onFeedback={feedback} feedbackSent={feedbackSent && index === turns.length - 1} /></div></div></div>)}
      {loading && <div className="message-row assistant-row"><span className="message-avatar assistant-avatar"><IconSpark size={17} /></span><div className="message-bubble assistant-bubble loading-bubble"><span className="typing-dots"><i /><i /><i /></span><span>{t.ragSearching}</span></div></div>}
      <div ref={endRef} />
    </div>
    <form className="chat-composer" onSubmit={submit}>
      <div className="consultation-context">
        <CustomSelect
          ariaLabel="User type"
          value={userType}
          onChange={setUserType}
          options={[{ value: "", label: c.userType }, { value: "worker", label: c.worker }, { value: "student", label: c.student }]}
        />
        <input aria-label="Region" value={region} onChange={(event) => setRegion(event.target.value)} placeholder={c.region} maxLength={80} />
        <button type="button" className={location ? "active" : ""} onClick={useLocation}><IconPin size={15} />{c.location}</button>
      </div>
      <div className="composer-row">
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={onComposerKeyDown} onCompositionEnd={onComposerCompositionEnd} placeholder={t.chatPlaceholder} maxLength={1000} rows={2} />
        <button className="primary composer-send" disabled={loading || question.trim().length < 2} aria-label={t.send}>{loading ? "…" : <IconSend size={22} />}</button>
      </div>
      <div className="question-meta"><small><IconLock size={14} />{t.noPersonal}</small><span>{question.length}/1000</span></div>
      {error && <p className="inline-error">{error}</p>}
    </form>
    {turns.length > 0 && <button className="secondary reset-button new-chat-button" onClick={reset}><IconPlus size={16} />{language === "ko" ? "새 상담 시작" : language === "en" ? "New conversation" : "Cuộc trò chuyện mới"}</button>}
  </section>;
}
