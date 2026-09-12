"use client";

import Link from "next/link";
import { FormEvent, useEffect, useRef, useState } from "react";
import { ApiError, ConsultationResponse, createConsultation, sendFeedback } from "../lib/api";
import { Language, localized, messages, withLanguage } from "../lib/i18n";

type Turn = { id: string; question: string; answer: ConsultationResponse };

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

function AssistantAnswer({ answer, language, onFeedback, feedbackSent }: { answer: ConsultationResponse; language: Language; onFeedback: (rating: "helpful" | "not_helpful") => void; feedbackSent: boolean }) {
  const t = messages[language];
  return <div className="assistant-content">
    <div className="assistant-label"><span className={`answer-label ${answer.answer_mode}`}>{answerLabel(answer, language)}</span>{answer.cached ? ` · ${t.cachedAnswer}` : ""}</div>
    <p className="generated-answer">{answer.message}</p>
    {answer.answer_mode === "insufficient_evidence" && <div className="urgent-notice">{t.insufficient}</div>}
    {answer.answer_mode !== "rag" && answer.answer_mode !== "ai" && <div className="location-note">{t.fallbackNotice}</div>}
    {answer.evidence_sufficient && <div className="privacy-note">✓ {t.evidenceNote}</div>}
    {answer.urgent_notice && <div className="urgent-notice">⚠ {answer.urgent_notice}</div>}
    {answer.sources.length > 0 && <section className="chat-extra"><h3>{t.sourceDocuments}</h3><div className="source-list">{answer.sources.map((source) => <a href={source.url} target="_blank" rel="noreferrer" key={source.chunk_id}><strong>{source.title}<b className={`trust-badge ${source.trust_level}`}>{trustLabel(source.trust_level, language)}</b></strong><span>{source.publisher} · v{source.document_version} · {language === "ko" ? "관련도" : language === "en" ? "Relevance" : "Mức liên quan"} {(source.relevance * 100).toFixed(0)}% · {language === "ko" ? "권위" : language === "en" ? "Authority" : "Thẩm quyền"} {(source.authority_score * 100).toFixed(0)}%</span><small>{sourceDateLabel(source, language)}{source.effective_from ? ` · ${language === "ko" ? "시행일" : language === "en" ? "Effective" : "Có hiệu lực"} ${source.effective_from}` : ""}{source.last_checked_at ? ` · ${language === "ko" ? "마지막 확인" : language === "en" ? "Checked" : "Kiểm tra"} ${source.last_checked_at.slice(0, 10)}` : ""}{sourceFreshnessLabel(source, language) ? ` · ${sourceFreshnessLabel(source, language)}` : ""}{source.trust_reasons.length ? ` · ${source.trust_reasons.join(" · ")}` : ""}</small></a>)}</div></section>}
    {answer.guides.length > 0 && <section className="chat-extra"><h3>{t.relatedGuide}</h3><div className="chat-guide-list">{answer.guides.map((guide) => <Link href={withLanguage(`/guides/${guide.id}`, language)} key={guide.id}><span className={`category-badge ${guide.category}`}>{guide.category === "residency" ? t.residency : t.labor}</span><strong>{localized(guide.title, language)}</strong><small>{localized(guide.summary, language)}</small></Link>)}</div></section>}
    {answer.follow_up_questions.length > 0 && <section className="chat-extra"><h3>{t.followUp}</h3><ul>{answer.follow_up_questions.map((item) => <li key={item}>{item}</li>)}</ul></section>}
    {answer.agencies.length > 0 && <section className="chat-extra"><h3>{t.help}</h3><div className="answer-agencies">{answer.agencies.map((agency) => <div key={agency.id}><strong>{localized(agency.name, language)}</strong><a href={`tel:${agency.phone}`}>☎ {agency.phone}{agency.distance_km !== null ? ` · ${agency.distance_km} km` : ""}</a></div>)}</div></section>}
    <div className="chat-feedback">{feedbackSent ? <span>{t.feedbackThanks}</span> : <><span>{t.feedbackQuestion}</span><button onClick={() => onFeedback("helpful")}>👍 {t.helpful}</button><button onClick={() => onFeedback("not_helpful")}>👎 {t.notHelpful}</button></>}</div>
  </div>;
}

export function ChatClient({ language }: { language: Language }) {
  const t = messages[language];
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [userType, setUserType] = useState("");
  const [region, setRegion] = useState("");
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [turns, loading]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (text.length < 2 || loading) return;
    setQuestion(""); setLoading(true); setError(""); setFeedbackSent(false);
    try {
      const conversation_context = turns.slice(-3).map((turn) => turn.question).join("\n").slice(-2200) || undefined;
      const answer = await createConsultation(text, language, { user_type: userType || undefined, region: region || undefined, conversation_context, ...location });
      setTurns((previous) => [...previous, { id: answer.consultation_id || `${Date.now()}`, question: text, answer }]);
    } catch (requestError) {
      setQuestion(text);
      setError(requestError instanceof ApiError && requestError.status === 429 ? "Too many requests · 잠시 후 다시 시도해 주세요." : "Unable to connect · 연결 상태를 확인해 주세요.");
    } finally { setLoading(false); }
  }

  function reset() { setQuestion(""); setTurns([]); setError(""); setFeedbackSent(false); }
  function useLocation() { if (navigator.geolocation) navigator.geolocation.getCurrentPosition(({ coords }) => setLocation({ latitude: coords.latitude, longitude: coords.longitude })); }
  async function feedback(rating: "helpful" | "not_helpful") { const answer = turns.at(-1)?.answer; if (!answer?.consultation_id || feedbackSent) return; try { await sendFeedback(answer.consultation_id, rating); setFeedbackSent(true); } catch { setError("Unable to send feedback."); } }

  return <section className="chat-shell chatbot-shell content-width">
    <div className="chat-heading"><div className="eyebrow">JB BRIDGE CONSULTATION</div><h1>{t.chatTitle}</h1><p>{t.chatDescription}</p></div>
    <div className="chat-window">
      {turns.length === 0 && <div className="chat-welcome"><span className="chat-avatar">✦</span><h2>{language === "ko" ? "안녕하세요. 무엇을 도와드릴까요?" : language === "en" ? "Hello. How can I help?" : "Xin chào. Tôi có thể giúp gì?"}</h2><p>{t.chatDescription}<br />{t.noPersonal}</p><div className="suggestion-list"><button onClick={() => setQuestion(t.chatPlaceholder.replace("예: ", ""))}>{t.chatPlaceholder}</button><button onClick={() => setQuestion(language === "ko" ? "임금체불이 발생했는데 어떻게 해야 하나요?" : language === "en" ? "What should I do about unpaid wages?" : "Tôi nên làm gì khi bị nợ lương?")}>{language === "ko" ? "임금체불 도움받기" : language === "en" ? "Get help with unpaid wages" : "Hỗ trợ khi bị nợ lương"}</button></div></div>}
      {turns.map((turn, index) => <div className="chat-turn" key={turn.id}><div className="message-row user-row"><span className="message-avatar user-avatar">나</span><div className="message-bubble user-bubble"><p>{turn.question}</p></div></div><div className="message-row assistant-row"><span className="message-avatar assistant-avatar">✦</span><div className="message-bubble assistant-bubble"><AssistantAnswer answer={turn.answer} language={language} onFeedback={feedback} feedbackSent={feedbackSent && index === turns.length - 1} /></div></div></div>)}
      {loading && <div className="message-row assistant-row"><span className="message-avatar assistant-avatar">✦</span><div className="message-bubble assistant-bubble loading-bubble"><span className="typing-dots"><i /><i /><i /></span><span>{t.ragSearching}</span></div></div>}
      <div ref={endRef} />
    </div>
    <form className="chat-composer" onSubmit={submit}><div className="consultation-context"><select aria-label="User type" value={userType} onChange={(event) => setUserType(event.target.value)}><option value="">사용자 유형 (선택)</option><option value="worker">외국인 근로자</option><option value="student">유학생</option></select><input aria-label="Region" value={region} onChange={(event) => setRegion(event.target.value)} placeholder="지역 (예: 전주)" maxLength={80} /><button type="button" onClick={useLocation}>📍 위치</button></div><div className="composer-row"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={t.chatPlaceholder} maxLength={1000} rows={2} /><button className="primary composer-send" disabled={loading || question.trim().length < 2} aria-label={t.send}>{loading ? "…" : "↑"}</button></div><div className="question-meta"><small>🔒 {t.noPersonal}</small><span>{question.length}/1000</span></div>{error && <p className="inline-error">{error}</p>}</form>
    {turns.length > 0 && <button className="secondary reset-button new-chat-button" onClick={reset}>＋ {language === "ko" ? "새 상담 시작" : language === "en" ? "New conversation" : "Cuộc trò chuyện mới"}</button>}
  </section>;
}
