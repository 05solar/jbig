# FastAPI 앱과 전체 API 엔드포인트(상담·가이드·기관·문서분석·지역해석·RAG 관리자)를 정의하는 파일
from uuid import uuid4
from contextlib import asynccontextmanager
from math import asin, cos, radians, sin, sqrt
from secrets import compare_digest

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .chat.ai_consultation import generate_grounded_answer, generate_rag_answer, rewrite_search_query, select_guide_semantically
from .chat.consultation import build_consultation, consult
from .data.seed import AGENCIES, GUIDES
from .infra.database import approve_rag_version, database_available, get_rag_document_summary, initialize_database, list_pending_rag_versions, load_agencies, load_guides, rag_document_status, rag_index_version, reject_rag_version, save_consultation, save_pending_rag_version
from .retrieval.embeddings import search_guides_semantically
from .documents.document_explanation import explain_document
from .retrieval.rag import content_hash, index_approved_document, index_documents, register_document, search_index, source_from_chunk
from .infra.operations import allow_request, cache_key, get_cached, hash_identifier, record_feedback, set_cached, status
from .data.regions import resolve_region
from .core.schemas import Agency, Category, ConsultationRequest, ConsultationResponse, DocumentExplanation, FeedbackRequest, FeedbackResponse, Guide, HealthResponse, Language, OperationsStatus, RAGDocumentAdminResponse, RAGDocumentCreate, RegionInfo

@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    if settings.rag_embedding_warmup:
        from .retrieval import embedding_service
        embedding_service.warmup()
    yield


app = FastAPI(
    title="JB Bridge AI API",
    description="전북 외국인 주민 정착지원 플랫폼 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="jb-bridge-api", version="0.1.0", storage="postgresql" if database_available() else "memory")


@app.get("/api/guides", response_model=list[Guide])
def list_guides(category: Category | None = Query(default=None)) -> list[Guide]:
    stored = load_guides(category)
    if stored is not None:
        return stored
    if category is None:
        return GUIDES
    return [guide for guide in GUIDES if guide.category == category]


@app.get("/api/guides/{guide_id}", response_model=Guide)
def get_guide(guide_id: str) -> Guide:
    guides = load_guides()
    guide = next((item for item in guides if item.id == guide_id), None) if guides is not None else next((item for item in GUIDES if item.id == guide_id), None)
    if guide is None:
        raise HTTPException(status_code=404, detail="Guide not found")
    return guide


@app.get("/api/regions/resolve", response_model=RegionInfo)
def resolve_region_api(latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180)) -> RegionInfo:
    return resolve_region(latitude, longitude)


@app.get("/api/agencies", response_model=list[Agency])
def list_agencies(region: str | None = Query(None), service_type: str | None = Query(None), language: str | None = Query(None), latitude: float | None = Query(None, ge=-90, le=90), longitude: float | None = Query(None, ge=-180, le=180)) -> list[Agency]:
    agencies = load_agencies() or AGENCIES
    if region:
        agencies = [agency for agency in agencies if agency.region == region]
    if service_type:
        agencies = [agency for agency in agencies if service_type in agency.service_types]
    if language:
        agencies = [agency for agency in agencies if language in agency.supported_languages]
    if latitude is not None and longitude is not None:
        def with_distance(agency: Agency) -> Agency:
            if agency.latitude is None or agency.longitude is None:
                return agency
            lat1, lon1, lat2, lon2 = map(radians, [latitude, longitude, agency.latitude, agency.longitude])
            distance = 6371 * 2 * asin(sqrt(sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2))
            return agency.model_copy(update={"distance_km": round(distance, 1)})
        agencies = [with_distance(agency) for agency in agencies]
        agencies.sort(key=lambda agency: agency.distance_km if agency.distance_km is not None else float("inf"))
    return agencies


@app.get("/api/agencies/{agency_id}", response_model=Agency)
def get_agency(agency_id: str) -> Agency:
    agencies = load_agencies()
    agency = next((item for item in agencies if item.id == agency_id), None) if agencies is not None else next((item for item in AGENCIES if item.id == agency_id), None)
    if agency is None:
        raise HTTPException(status_code=404, detail="Agency not found")
    return agency


@app.post("/api/consultations", response_model=ConsultationResponse)
def create_consultation(payload: ConsultationRequest, request: Request) -> ConsultationResponse:
    client_hash = hash_identifier(request.client.host if request.client else "unknown")
    if not allow_request(client_hash):
        raise HTTPException(status_code=429, detail="Too many consultation requests. Try again shortly.")
    key = cache_key(payload.question, payload.language or "auto", payload.user_type, payload.region, rag_index_version(), payload.conversation_context)
    cached = get_cached(key)
    if cached:
        return cached
    search_question = f"{payload.conversation_context}\n{payload.question}" if payload.conversation_context else payload.question
    result = consult(search_question, payload.language)
    matches = search_index(search_question)
    if not matches:
        rewritten = rewrite_search_query(payload.question, safety_identifier=client_hash)
        if rewritten:
            matches = search_index(rewritten)
    if matches:
        result = generate_rag_answer(result, payload.question, matches, safety_identifier=client_hash)
        # Keep RAG as the answer mode while using the existing semantic guide
        # selector only to attach optional FAQ recommendations.
        if not result.guides and settings.openai_api_key:
            faq_result = select_guide_semantically(result, payload.question, safety_identifier=client_hash)
            if faq_result.guides:
                result = result.model_copy(update={"guide": faq_result.guide, "guides": faq_result.guides})
        service_types = {"immigration" if category == "residency" else "labor" for category in result.categories}
        recommended: list[Agency] = []
        for service_type in service_types:
            recommended.extend(list_agencies(region=None, service_type=service_type, language=payload.language, latitude=payload.latitude, longitude=payload.longitude))
        result = result.model_copy(update={"agencies": list({agency.id: agency for agency in recommended}.values())})
    else:
        if not result.guides:
            vector_guides = search_guides_semantically(payload.question)
            if vector_guides:
                result = build_consultation(vector_guides, result.language)
        result = select_guide_semantically(result, payload.question, safety_identifier=client_hash)
        result = generate_grounded_answer(result, payload.question, safety_identifier=client_hash)
        if not result.guides and not matches:
            follow_ups = {"ko": ["어떤 기관에 문의해야 하는지 함께 확인할 수 있도록 지역과 상황을 조금 더 알려주세요."], "en": ["Please share your region and a little more detail so we can direct you to the right agency."], "vi": ["Vui lòng cho biết khu vực và thêm một chút thông tin để chúng tôi hướng dẫn đúng cơ quan."]}
            result = result.model_copy(update={"answer_mode": "insufficient_evidence", "evidence_sufficient": False, "follow_up_questions": follow_ups.get(result.language, follow_ups["ko"])})
    result = result.model_copy(update={"consultation_id": uuid4().hex})
    set_cached(key, result)
    save_consultation(result, key)
    return result


@app.get("/api/rag/search")
def debug_rag_search(q: str = Query(min_length=2), category: Category | None = Query(default=None)):
    if not settings.rag_debug_enabled:
        raise HTTPException(status_code=404, detail="RAG debug endpoint is disabled")
    return [source_from_chunk(chunk, score).model_dump() for chunk, score in search_index(q, category=category)]


def require_rag_admin(token: str | None) -> None:
    if not settings.rag_admin_token:
        raise HTTPException(status_code=503, detail="RAG administration is not configured")
    if not token or not compare_digest(token, settings.rag_admin_token):
        raise HTTPException(status_code=401, detail="Invalid RAG administrator token")


@app.get("/api/admin/rag/status")
def rag_admin_status(x_rag_admin_token: str | None = Header(default=None)):
    require_rag_admin(x_rag_admin_token)
    return rag_document_status()


@app.get("/api/admin/rag/pending")
def rag_admin_pending(x_rag_admin_token: str | None = Header(default=None)):
    require_rag_admin(x_rag_admin_token)
    return list_pending_rag_versions() or []


@app.post("/api/admin/rag/versions/{version_id}/approve")
def approve_rag_document_version(version_id: str, reviewed_by: str = Query(min_length=2, max_length=120), note: str = Query(default="", max_length=1000), x_rag_admin_token: str | None = Header(default=None)):
    require_rag_admin(x_rag_admin_token)
    document_id = approve_rag_version(version_id, reviewed_by, note)
    if not document_id:
        raise HTTPException(status_code=404, detail="Pending document version not found")
    embedding = index_approved_document(document_id)
    return {"approved": True, "version_id": version_id, "document_id": document_id, "embedding": embedding, "index_version": rag_index_version()}


@app.post("/api/admin/rag/versions/{version_id}/reject")
def reject_rag_document_version(version_id: str, reviewed_by: str = Query(min_length=2, max_length=120), note: str = Query(min_length=2, max_length=1000), x_rag_admin_token: str | None = Header(default=None)):
    require_rag_admin(x_rag_admin_token)
    if not reject_rag_version(version_id, reviewed_by, note):
        raise HTTPException(status_code=404, detail="Pending document version not found")
    return {"rejected": True, "version_id": version_id}


@app.post("/api/admin/rag/documents", response_model=RAGDocumentAdminResponse)
def register_rag_document_api(payload: RAGDocumentCreate, x_rag_admin_token: str | None = Header(default=None)) -> RAGDocumentAdminResponse:
    require_rag_admin(x_rag_admin_token)
    if not database_available():
        raise HTTPException(status_code=503, detail="PostgreSQL is required for document registration")
    try:
        document, chunks = register_document(document_id=payload.document_id, title=payload.title, publisher=payload.publisher, category=payload.category, text=payload.original_text, source_url=payload.source_url, language=payload.language, issued_at=payload.issued_at, verified_at=payload.verified_at, version=payload.version, active=payload.active, document_type=payload.document_type, published_at=payload.published_at, promulgated_at=payload.promulgated_at, effective_from=payload.effective_from, effective_until=payload.effective_until)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    current = get_rag_document_summary(document.document_id)
    if current and current["content_hash"] != document.content_hash:
        pending = document.model_copy(update={"version": str(int(current["version"]) + 1) if current["version"].isdigit() else f"{current['version']}-updated", "version_id": f"{document.document_id}:pending:{document.content_hash[:12]}", "active": False, "status": "review_pending", "previous_version_id": current["version_id"] or None})
        saved = save_pending_rag_version(pending, [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks])
        return RAGDocumentAdminResponse(document_id=document.document_id, indexed=False, chunks=len(chunks), content_hash=document.content_hash, message="Changed document is pending review" if saved else "Changed version is already pending")
    if current:
        return RAGDocumentAdminResponse(document_id=document.document_id, indexed=False, chunks=len(chunks), content_hash=document.content_hash, message="Document content is unchanged")
    indexed, _ = index_documents(documents=((document, chunks),))
    return RAGDocumentAdminResponse(document_id=document.document_id, indexed=bool(indexed), chunks=len(chunks), content_hash=document.content_hash, message="Document indexed" if indexed else "Document was not indexed")


@app.post("/api/feedback", response_model=FeedbackResponse)
def create_feedback(payload: FeedbackRequest) -> FeedbackResponse:
    return FeedbackResponse(accepted=record_feedback(payload))


@app.get("/api/operations/status", response_model=OperationsStatus)
def get_operations_status() -> OperationsStatus:
    return status()


@app.post("/api/documents/explain", response_model=DocumentExplanation)
async def create_document_explanation(request: Request, file: UploadFile = File(...), language: Language = Form("ko"), allow_unredacted_file: bool = Form(False)) -> DocumentExplanation:
    client_hash = hash_identifier(request.client.host if request.client else "unknown")
    if not allow_request(client_hash):
        raise HTTPException(status_code=429, detail="Too many requests")
    content = await file.read(settings.document_max_bytes + 1)
    try:
        return explain_document(content, file.content_type or "", file.filename or "document", language, allow_unredacted_file)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
