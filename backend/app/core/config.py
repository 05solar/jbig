# 환경변수 기반 전체 설정(RAG·임베딩·OCR·운영 한도)을 정의하는 파일
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = (
        "postgresql://jb_bridge:local_development_only@localhost:5432/jb_bridge"
    )
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_timeout_seconds: float = 15.0
    consultation_rate_limit: int = 10
    consultation_cache_seconds: int = 600
    daily_ai_call_limit: int = 200
    identifier_salt: str = "change-this-in-production"
    database_enabled: bool = True
    database_connect_timeout: int = 2
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 384
    rag_embedding_provider: str = "local"  # local | openai | none
    rag_local_embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    rag_local_embedding_device: str = "cpu"
    rag_embedding_warmup: bool = False
    rag_model_cache_dir: str | None = None
    rag_db_lexical_candidates: int = 20
    rag_db_vector_candidates: int = 20
    # MiniLM cosine for unrelated Korean prose sits around 0.5~0.6; below this the
    # vector channel adds noise that drowns lexically-correct matches (measured on
    # the 59-document corpus). High-confidence vector matches still contribute.
    rag_db_vector_similarity_threshold: float = 0.60
    vector_similarity_threshold: float = 0.44
    document_max_bytes: int = 5_000_000
    ocr_enabled: bool = True
    ocr_language: str = "korean"
    ocr_min_confidence: float = 0.60
    ocr_max_pages: int = 5
    ocr_min_pdf_text_chars: int = 40
    rag_top_k: int = 6
    rag_similarity_threshold: float = 0.35
    rag_weight_lexical: float = 1.0
    rag_weight_vector: float = 1.0
    rag_weight_authority: float = 0.15
    rag_weight_freshness: float = 0.05
    rag_max_evidence: int = 4
    rag_max_chunks_per_document: int = 2
    rag_min_confident_relevance: float = 0.35
    rag_query_rewrite_enabled: bool = False
    rag_document_max_queries: int = 8
    rag_use_sample_documents_for_tests: bool = False
    rag_debug_enabled: bool = False
    rag_allowed_domains: str = "law.go.kr,open.law.go.kr,moj.go.kr,immigration.go.kr,hikorea.go.kr,moel.go.kr,minimumwage.go.kr,nlrc.go.kr,comwel.or.kr,jeonbuk.go.kr,liveinkorea.kr,gov.kr"
    rag_index_version: str = "1"
    crawler_enabled: bool = True
    crawler_user_agent: str = "JB-Bridge-OfficialCrawler/1.0 (+https://github.com/05solar/jbig)"
    crawler_request_delay_ms: int = 1000
    crawler_max_concurrency: int = 2
    crawler_timeout_seconds: float = 10.0
    crawler_min_content_chars: int = 300
    crawler_max_retries: int = 3
    crawler_max_detail_pages: int = 50
    crawler_respect_robots: bool = True
    rag_admin_token: str | None = None
    rag_update_enabled: bool = True
    source_fetch_timeout: float = 15.0
    source_max_response_bytes: int = 5_000_000
    source_max_redirects: int = 3
    source_check_interval_law: int = 86400
    source_check_interval_notice: int = 21600
    source_check_interval_guide: int = 604800
    source_stale_warning_days: int = 14

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
