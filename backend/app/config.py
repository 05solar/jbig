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
    embedding_dimensions: int = 512
    vector_similarity_threshold: float = 0.55
    document_max_bytes: int = 5_000_000
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
    rag_debug_enabled: bool = False
    rag_allowed_domains: str = "law.go.kr,open.law.go.kr,moj.go.kr,immigration.go.kr,hikorea.go.kr,moel.go.kr,minimumwage.go.kr,nlrc.go.kr,comwel.or.kr,jeonbuk.go.kr,liveinkorea.kr,gov.kr"
    rag_index_version: str = "1"
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
