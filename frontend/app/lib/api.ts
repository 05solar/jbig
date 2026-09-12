// 백엔드 API 타입 정의와 fetch 클라이언트를 담당하는 파일
export type Category = "residency" | "labor";

export type GuideReference = { title: string; url: string; publisher: string };

export type Guide = {
  id: string;
  category: Category;
  title: Record<string, string>;
  summary: Record<string, string>;
  steps: Record<string, string[]>;
  required_documents: Record<string, string[]>;
  cautions: Record<string, string[]>;
  agency_ids: string[];
  source_name: Record<string, string>;
  source_url: string;
  verified_at: string;
  target: Record<string, string>;
  common_mistakes: Record<string, string[]>;
  related_documents: GuideReference[];
};

export type Agency = {
  id: string;
  name: Record<string, string>;
  description: Record<string, string>;
  phone: string;
  website: string;
  address: string;
  region: string;
  service_types: string[];
  supported_languages: string[];
  hours: Record<string, string>;
  latitude: number | null;
  longitude: number | null;
  emergency: boolean;
  verified_at: string;
  distance_km: number | null;
};

export type AgencySearchParams = {
  region?: string;
  serviceType?: string;
  language?: string;
  latitude?: number;
  longitude?: number;
};

export type ConsultationResponse = {
  consultation_id: string;
  language: "ko" | "en" | "vi";
  message: string;
  guide: Guide | null;
  guides: Guide[];
  agencies: Agency[];
  urgent_notice: string | null;
  answer_mode: "rag" | "ai" | "guide_fallback" | "rule_fallback" | "insufficient_evidence" | "rules";
  cached: boolean;
  categories: Category[];
  intents: string[];
  sources: RAGSource[];
  evidence_sufficient: boolean;
  follow_up_questions: string[];
};

export type RAGSource = { document_id: string; chunk_id: string; title: string; publisher: string; url: string; url_specific: boolean; display_title: string | null; display_publisher: string | null; source_summary: string | null; verified_at: string; relevance: number; document_version: string; published_at: string | null; collected_at: string | null; effective_from: string | null; last_checked_at: string | null; freshness_type: "versioned" | "periodically_checked" | "live_verification_required"; freshness_status: string; document_type: string; authority_score: number; trust_level: "high" | "medium" | "low"; trust_reasons: string[] };

export type RiskItem = {
  level: "SAFE" | "CHECK" | "WARNING";
  clause: string;
  reason: string;
  recommendation: string;
  checks: string[];
  sources: RAGSource[];
  title: string;
  official_standard: string;
  problem: string;
  impact: string;
  recommended_revision: string;
  detected_value: string | null;
  official_value: string | null;
  difference: string | null;
};

export type DocumentExplanation = {
  language: "ko" | "en" | "vi";
  summary: string;
  key_points: string[];
  actions: string[];
  deadlines: string[];
  cautions: string[];
  related_guides: Guide[];
  privacy_redacted: boolean;
  document_type: string;
  key_terms: Record<string, string>;
  risk_items: RiskItem[];
  ocr_used: boolean;
  ocr_confidence: number | null;
  original_text: string;
};

export type RegionInfo = { region: string | null; name: Record<string, string> | null };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
  if (!response.ok) throw new ApiError(response.status, `API request failed: ${response.status}`);
  return response.json() as Promise<T>;
}

export const getGuides = (category?: Category) =>
  apiFetch<Guide[]>(`/api/guides${category ? `?category=${category}` : ""}`);

export const getGuide = (id: string) => apiFetch<Guide>(`/api/guides/${id}`);

export const resolveRegion = (latitude: number, longitude: number) =>
  apiFetch<RegionInfo>(`/api/regions/resolve?latitude=${latitude}&longitude=${longitude}`);

export const getAgencies = (params: AgencySearchParams = {}) => {
  const query = new URLSearchParams();
  if (params.region) query.set("region", params.region);
  if (params.serviceType) query.set("service_type", params.serviceType);
  if (params.language) query.set("language", params.language);
  if (params.latitude !== undefined) query.set("latitude", String(params.latitude));
  if (params.longitude !== undefined) query.set("longitude", String(params.longitude));
  const suffix = query.size ? `?${query.toString()}` : "";
  return apiFetch<Agency[]>(`/api/agencies${suffix}`);
};

export async function createConsultation(question: string, language: "ko" | "en" | "vi", context: { user_type?: string; region?: string; latitude?: number; longitude?: number; conversation_context?: string } = {}) {
  const response = await fetch(`${API_URL}/api/consultations`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, language, ...context }) });
  if (!response.ok) throw new ApiError(response.status, `API request failed: ${response.status}`);
  return response.json() as Promise<ConsultationResponse>;
}

export async function sendFeedback(consultationId: string, rating: "helpful" | "not_helpful") {
  const response = await fetch(`${API_URL}/api/feedback`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ consultation_id: consultationId, rating }) });
  if (!response.ok) throw new ApiError(response.status, `API request failed: ${response.status}`);
  return response.json() as Promise<{ accepted: boolean }>;
}

export async function explainDocument(file: File, language: "ko" | "en" | "vi", consent: boolean) {
  const form = new FormData();
  form.append("file", file); form.append("language", language); form.append("allow_unredacted_file", String(consent));
  const response = await fetch(`${API_URL}/api/documents/explain`, { method: "POST", body: form });
  if (!response.ok) throw new ApiError(response.status, await response.text());
  return response.json() as Promise<DocumentExplanation>;
}
