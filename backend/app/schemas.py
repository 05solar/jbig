# API 요청/응답과 RAG 문서·출처·위험항목의 Pydantic 스키마를 정의하는 파일
from typing import Literal

from pydantic import BaseModel, Field


Category = Literal["residency", "labor"]
Language = Literal["ko", "en", "vi"]


class GuideReference(BaseModel):
    title: str
    url: str
    publisher: str


class Guide(BaseModel):
    id: str
    category: Category
    title: dict[str, str]
    summary: dict[str, str]
    steps: dict[str, list[str]]
    required_documents: dict[str, list[str]]
    cautions: dict[str, list[str]]
    agency_ids: list[str]
    source_name: dict[str, str]
    source_url: str
    verified_at: str
    target: dict[str, str] = Field(default_factory=dict)
    common_mistakes: dict[str, list[str]] = Field(default_factory=dict)
    related_documents: list[GuideReference] = Field(default_factory=list)


class Agency(BaseModel):
    id: str
    name: dict[str, str]
    description: dict[str, str]
    phone: str
    website: str
    address: str
    region: str = "jeonbuk"
    service_types: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=lambda: ["ko"])
    hours: dict[str, str] = Field(default_factory=dict)
    latitude: float | None = None
    longitude: float | None = None
    emergency: bool = False
    verified_at: str = "2026-09-12"
    distance_km: float | None = None


class RAGSource(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    publisher: str
    url: str
    url_specific: bool = True
    display_title: str | None = None
    display_publisher: str | None = None
    source_summary: str | None = None
    verified_at: str
    relevance: float
    document_version: str = "1"
    published_at: str | None = None
    collected_at: str | None = None
    effective_from: str | None = None
    last_checked_at: str | None = None
    freshness_type: Literal["versioned", "periodically_checked", "live_verification_required"] = "versioned"
    freshness_status: str = "최신 공식자료 확인 완료"
    document_type: str = "guide"
    authority_score: float = 0.8
    trust_level: Literal["high", "medium", "low"] = "medium"
    trust_reasons: list[str] = Field(default_factory=list)


class RAGDocument(BaseModel):
    document_id: str
    title: str
    publisher: str
    category: Category
    original_text: str
    source_url: str
    language: str
    issued_at: str | None = None
    collected_at: str
    verified_at: str
    version: str
    content_hash: str
    active: bool = True
    version_id: str = ""
    source_organization: str = ""
    source_domain: str = ""
    document_type: str = "guide"
    published_at: str | None = None
    promulgated_at: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None
    retrieved_at: str | None = None
    last_checked_at: str | None = None
    next_check_at: str | None = None
    index_version: str = "1"
    status: Literal["active", "review_pending", "approved", "superseded", "inactive", "expired", "fetch_failed"] = "active"
    previous_version_id: str | None = None
    change_detected_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    review_note: str | None = None
    fetch_failures: int = 0
    last_fetch_error: str | None = None


class RAGChunk(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    embedding: list[float] | None = None


class RAGDocumentCreate(BaseModel):
    document_id: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    title: str = Field(min_length=2, max_length=300)
    publisher: str = Field(min_length=2, max_length=200)
    category: Category
    original_text: str = Field(min_length=20, max_length=500_000)
    source_url: str
    language: str = Field(default="ko", max_length=20)
    issued_at: str | None = Field(default=None, max_length=30)
    verified_at: str | None = Field(default=None, max_length=30)
    version: str = Field(default="1", max_length=80)
    active: bool = True
    document_type: str = Field(default="guide", max_length=40)
    published_at: str | None = None
    promulgated_at: str | None = None
    effective_from: str | None = None
    effective_until: str | None = None


class RAGDocumentAdminResponse(BaseModel):
    document_id: str
    indexed: bool
    chunks: int
    content_hash: str
    message: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    storage: Literal["postgresql", "memory"]


class ConsultationRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    language: Language | None = None
    user_type: str | None = Field(default=None, max_length=40)
    region: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    conversation_context: str | None = Field(default=None, max_length=2500)


class ConsultationResponse(BaseModel):
    consultation_id: str = ""
    language: Language
    message: str
    guide: Guide | None
    guides: list[Guide] = Field(default_factory=list)
    agencies: list[Agency]
    urgent_notice: str | None = None
    answer_mode: Literal["rag", "ai", "guide_fallback", "rule_fallback", "insufficient_evidence", "rules"] = "rules"
    cached: bool = False
    categories: list[Category] = Field(default_factory=list)
    intents: list[str] = Field(default_factory=list)
    sources: list[RAGSource] = Field(default_factory=list)
    evidence_sufficient: bool = False
    follow_up_questions: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    consultation_id: str = Field(min_length=8, max_length=64)
    rating: Literal["helpful", "not_helpful"]
    reason: Literal["wrong_guide", "unclear", "missing_information", "other"] | None = None


class FeedbackResponse(BaseModel):
    accepted: bool = True


class OperationsStatus(BaseModel):
    consultations: int
    cache_hits: int
    ai_calls: int
    ai_fallbacks: int
    helpful: int
    not_helpful: int


class RiskItem(BaseModel):
    level: Literal["SAFE", "CHECK", "WARNING"]
    clause: str
    reason: str
    recommendation: str
    checks: list[str] = Field(default_factory=list)
    sources: list[RAGSource] = Field(default_factory=list)
    title: str = ""
    official_standard: str = ""
    problem: str = ""
    impact: str = ""
    recommended_revision: str = ""
    detected_value: str | None = None
    official_value: str | None = None
    difference: str | None = None


class DocumentExplanation(BaseModel):
    language: Language
    summary: str
    key_points: list[str]
    actions: list[str]
    deadlines: list[str]
    cautions: list[str]
    related_guides: list[Guide]
    privacy_redacted: bool
    document_type: str = "unknown"
    key_terms: dict[str, str] = Field(default_factory=dict)
    risk_items: list[RiskItem] = Field(default_factory=list)
    ocr_used: bool = False
    ocr_confidence: float | None = None
    original_text: str = ""


class RegionInfo(BaseModel):
    region: str | None = None
    name: dict[str, str] | None = None
