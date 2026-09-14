# PostgreSQL/pgvector 접근 계층(스키마 마이그레이션·문서/청크 저장·후보/벡터 검색·버전 승인)을 담당하는 파일
import json
import logging
import time
from contextlib import contextmanager
from datetime import date
from typing import Iterator

from ..core.config import settings
from ..data.seed import AGENCIES, GUIDES
from ..core.schemas import Agency, Category, ConsultationResponse, FeedbackRequest, Guide, OperationsStatus, RAGDocument

logger = logging.getLogger(__name__)
_unavailable_until = 0.0

# Shared column list for rag_documents joins; keep in sync with _document_from_row.
DOC_COLUMNS = "d.document_id,d.title,d.publisher,d.category,d.original_text,d.source_url,d.language,d.issued_at,d.collected_at,d.verified_at,d.version,d.content_hash,d.active,d.version_id,d.source_organization,d.source_domain,d.document_type,d.published_at,d.promulgated_at,d.effective_from,d.effective_until,d.retrieved_at,d.last_checked_at,d.next_check_at,d.index_version,d.status,d.previous_version_id,d.change_detected_at,d.reviewed_at,d.reviewed_by,d.review_note,d.fetch_failures,d.last_fetch_error"


def _document_from_row(row) -> RAGDocument:
    return RAGDocument(document_id=row[0], title=row[1], publisher=row[2], category=row[3], original_text=row[4], source_url=row[5], language=row[6], issued_at=row[7], collected_at=str(row[8]), verified_at=str(row[9]), version=row[10], content_hash=row[11], active=row[12], version_id=row[13] or "", source_organization=row[14] or row[2], source_domain=row[15] or "", document_type=row[16] or "guide", published_at=row[17], promulgated_at=row[18], effective_from=row[19], effective_until=row[20], retrieved_at=str(row[21]) if row[21] else None, last_checked_at=str(row[22]) if row[22] else None, next_check_at=str(row[23]) if row[23] else None, index_version=str(row[24] or "1"), status=row[25] or "active", previous_version_id=row[26], change_detected_at=str(row[27]) if row[27] else None, reviewed_at=str(row[28]) if row[28] else None, reviewed_by=row[29], review_note=row[30], fetch_failures=row[31] or 0, last_fetch_error=row[32])


@contextmanager
def connection() -> Iterator[object]:
    global _unavailable_until
    if not settings.database_enabled or time.monotonic() < _unavailable_until:
        raise ConnectionError("Database unavailable")
    try:
        import psycopg
        with psycopg.connect(settings.database_url, connect_timeout=settings.database_connect_timeout) as conn:
            yield conn
    except Exception:
        _unavailable_until = time.monotonic() + 30
        raise


def initialize_database() -> bool:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute("""CREATE TABLE IF NOT EXISTS agencies (id text PRIMARY KEY, data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS guides (id text PRIMARY KEY, category text NOT NULL CHECK (category IN ('residency','labor')), data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute(f"ALTER TABLE guides ADD COLUMN IF NOT EXISTS embedding vector({settings.embedding_dimensions})")
                cursor.execute("ALTER TABLE guides ADD COLUMN IF NOT EXISTS embedding_model text")
                cursor.execute("ALTER TABLE guides ADD COLUMN IF NOT EXISTS content_hash text")
                cursor.execute("""CREATE TABLE IF NOT EXISTS consultations (id text PRIMARY KEY, question_hash text NOT NULL, language text NOT NULL, answer_mode text NOT NULL, guide_ids jsonb NOT NULL, cached boolean NOT NULL DEFAULT false, created_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("""CREATE INDEX IF NOT EXISTS consultations_created_at_idx ON consultations (created_at)""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS feedback (consultation_id text PRIMARY KEY REFERENCES consultations(id) ON DELETE CASCADE, rating text NOT NULL CHECK (rating IN ('helpful','not_helpful')), reason text, created_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS daily_ai_usage (usage_date date PRIMARY KEY, calls integer NOT NULL DEFAULT 0)""")
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_documents (document_id text PRIMARY KEY, title text NOT NULL, publisher text NOT NULL, category text NOT NULL CHECK (category IN ('residency','labor')), original_text text NOT NULL, source_url text NOT NULL, language text NOT NULL, issued_at text, collected_at date NOT NULL, verified_at date NOT NULL, version text NOT NULL, content_hash text NOT NULL, active boolean NOT NULL DEFAULT true, updated_at timestamptz NOT NULL DEFAULT now())""")
                for column, definition in {
                    "version_id": "text", "source_organization": "text", "source_domain": "text", "document_type": "text NOT NULL DEFAULT 'guide'", "published_at": "text", "promulgated_at": "text", "effective_from": "text", "effective_until": "text", "retrieved_at": "timestamptz", "last_checked_at": "timestamptz", "next_check_at": "timestamptz", "index_version": "text NOT NULL DEFAULT '1'", "status": "text NOT NULL DEFAULT 'active'", "previous_version_id": "text", "change_detected_at": "timestamptz", "reviewed_at": "timestamptz", "reviewed_by": "text", "review_note": "text", "fetch_failures": "integer NOT NULL DEFAULT 0", "last_fetch_error": "text"
                }.items():
                    cursor.execute(f"ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS {column} {definition}")
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_chunks (chunk_id text PRIMARY KEY, document_id text NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE, chunk_index integer NOT NULL, text text NOT NULL, embedding vector(%s), embedding_model text, content_hash text NOT NULL, active boolean NOT NULL DEFAULT true)""" % settings.embedding_dimensions)
                cursor.execute("CREATE INDEX IF NOT EXISTS rag_chunks_document_idx ON rag_chunks (document_id, chunk_index)")
                cursor.execute("ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS search_tokens text[]")
                cursor.execute("CREATE INDEX IF NOT EXISTS rag_chunks_search_tokens_idx ON rag_chunks USING gin (search_tokens)")
                # Vector-dimension migration: only when a column holds no data —
                # a populated column with the wrong dimension is a loud error, never auto-destroyed.
                for table, column in (("rag_chunks", "embedding"), ("rag_version_chunks", "embedding"), ("guides", "embedding")):
                    cursor.execute("SELECT atttypmod FROM pg_attribute WHERE attrelid=%s::regclass AND attname=%s", (table, column))
                    row = cursor.fetchone()
                    current_dim = row[0] if row else None
                    if current_dim is not None and current_dim > 0 and current_dim != settings.embedding_dimensions:
                        cursor.execute(f"SELECT count(*) FROM {table} WHERE {column} IS NOT NULL")
                        populated = cursor.fetchone()[0]
                        if populated == 0:
                            cursor.execute(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE vector({settings.embedding_dimensions})")
                            logger.info("Migrated %s.%s to vector(%d)", table, column, settings.embedding_dimensions)
                        else:
                            logger.error("Embedding dimension mismatch on %s.%s: column is vector(%d) with %d populated rows but EMBEDDING_DIMENSIONS=%d. Re-embed or migrate manually.", table, column, current_dim, populated, settings.embedding_dimensions)
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_document_versions (version_id text PRIMARY KEY, document_id text NOT NULL, data jsonb NOT NULL, content_hash text NOT NULL, status text NOT NULL, previous_version_id text, change_detected_at timestamptz, reviewed_at timestamptz, reviewed_by text, review_note text, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(document_id, content_hash))""")
                cursor.execute("ALTER TABLE rag_document_versions ADD COLUMN IF NOT EXISTS crawl_quality_score real")
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_version_chunks (chunk_id text PRIMARY KEY, version_id text NOT NULL REFERENCES rag_document_versions(version_id) ON DELETE CASCADE, chunk_index integer NOT NULL, text text NOT NULL, content_hash text NOT NULL, embedding vector(%s), embedding_model text NOT NULL DEFAULT '')""" % settings.embedding_dimensions)
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_index_state (id boolean PRIMARY KEY DEFAULT true, index_version bigint NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL DEFAULT now())""")
                cursor.execute("INSERT INTO rag_index_state (id,index_version) VALUES (true,1) ON CONFLICT (id) DO NOTHING")
                cursor.execute("""CREATE TABLE IF NOT EXISTS rag_update_audit (id bigserial PRIMARY KEY, document_id text NOT NULL, version_id text, action text NOT NULL, detail jsonb NOT NULL DEFAULT '{}'::jsonb, created_at timestamptz NOT NULL DEFAULT now())""")
                for agency in AGENCIES:
                    cursor.execute("INSERT INTO agencies (id,data) VALUES (%s,%s::jsonb) ON CONFLICT (id) DO UPDATE SET data=EXCLUDED.data, updated_at=now()", (agency.id, agency.model_dump_json()))
                for guide in GUIDES:
                    cursor.execute("INSERT INTO guides (id,category,data) VALUES (%s,%s,%s::jsonb) ON CONFLICT (id) DO UPDATE SET category=EXCLUDED.category, data=EXCLUDED.data, updated_at=now()", (guide.id, guide.category, guide.model_dump_json()))
                cursor.execute("CREATE INDEX IF NOT EXISTS guides_embedding_hnsw_idx ON guides USING hnsw (embedding vector_cosine_ops)")
        logger.info("PostgreSQL initialized with %d guides and %d agencies", len(GUIDES), len(AGENCIES))
        return True
    except Exception as error:
        logger.warning("PostgreSQL unavailable; using memory fallback: %s", type(error).__name__)
        return False


def database_available() -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return cursor.fetchone()[0] == 1
    except Exception:
        return False


def load_guides(category: Category | None = None) -> list[Guide] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            if category:
                cursor.execute("SELECT data FROM guides WHERE category=%s ORDER BY id", (category,))
            else:
                cursor.execute("SELECT data FROM guides ORDER BY id")
            return [Guide.model_validate(row[0]) for row in cursor.fetchall()]
    except Exception:
        return None


def load_agencies() -> list[Agency] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT data FROM agencies ORDER BY id")
            return [Agency.model_validate(row[0]) for row in cursor.fetchall()]
    except Exception:
        return None


def embedding_hashes() -> dict[str, str | None] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT id, content_hash FROM guides")
            return dict(cursor.fetchall())
    except Exception:
        return None


def save_guide_embedding(guide_id: str, embedding: list[float], model: str, content_hash: str) -> bool:
    try:
        vector = "[" + ",".join(str(value) for value in embedding) + "]"
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("UPDATE guides SET embedding=%s::vector, embedding_model=%s, content_hash=%s WHERE id=%s", (vector, model, content_hash, guide_id))
        return True
    except Exception:
        return False


def search_guide_vectors(embedding: list[float], limit: int, threshold: float, model: str | None = None) -> list[tuple[Guide, float]] | None:
    try:
        vector = "[" + ",".join(str(value) for value in embedding) + "]"
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("""SELECT data, 1 - (embedding <=> %s::vector) AS similarity FROM guides WHERE embedding IS NOT NULL AND embedding_model=%s AND 1 - (embedding <=> %s::vector) >= %s ORDER BY embedding <=> %s::vector LIMIT %s""", (vector, model or settings.embedding_model, vector, threshold, vector, limit))
            return [(Guide.model_validate(row[0]), float(row[1])) for row in cursor.fetchall()]
    except Exception:
        return None


def save_rag_document(document: RAGDocument, chunks: list[tuple[str, int, str, str]], embeddings: list[list[float]] | None = None) -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT content_hash,active,version,source_url FROM rag_documents WHERE document_id=%s", (document.document_id,))
            current = cursor.fetchone()
            if current and current[0] == document.content_hash and current[1] == document.active and current[2] == document.version and current[3] == document.source_url:
                return False
            cursor.execute("""INSERT INTO rag_documents (document_id,title,publisher,category,original_text,source_url,language,issued_at,collected_at,verified_at,version,content_hash,active,version_id,source_organization,source_domain,document_type,published_at,promulgated_at,effective_from,effective_until,retrieved_at,last_checked_at,next_check_at,index_version,status,previous_version_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (document_id) DO UPDATE SET title=EXCLUDED.title,publisher=EXCLUDED.publisher,category=EXCLUDED.category,original_text=EXCLUDED.original_text,source_url=EXCLUDED.source_url,language=EXCLUDED.language,issued_at=EXCLUDED.issued_at,collected_at=EXCLUDED.collected_at,verified_at=EXCLUDED.verified_at,version=EXCLUDED.version,content_hash=EXCLUDED.content_hash,active=EXCLUDED.active,version_id=EXCLUDED.version_id,source_organization=EXCLUDED.source_organization,source_domain=EXCLUDED.source_domain,document_type=EXCLUDED.document_type,published_at=EXCLUDED.published_at,promulgated_at=EXCLUDED.promulgated_at,effective_from=EXCLUDED.effective_from,effective_until=EXCLUDED.effective_until,retrieved_at=EXCLUDED.retrieved_at,last_checked_at=EXCLUDED.last_checked_at,next_check_at=EXCLUDED.next_check_at,index_version=EXCLUDED.index_version,status=EXCLUDED.status,previous_version_id=EXCLUDED.previous_version_id,updated_at=now()""", (document.document_id, document.title, document.publisher, document.category, document.original_text, document.source_url, document.language, document.issued_at, document.collected_at, document.verified_at, document.version, document.content_hash, document.active, document.version_id, document.source_organization, document.source_domain, document.document_type, document.published_at, document.promulgated_at, document.effective_from, document.effective_until, document.retrieved_at, document.last_checked_at, document.next_check_at, document.index_version, document.status, document.previous_version_id))
            cursor.execute("INSERT INTO rag_document_versions (version_id,document_id,data,content_hash,status,previous_version_id) VALUES (%s,%s,%s::jsonb,%s,%s,%s) ON CONFLICT (version_id) DO NOTHING", (document.version_id or f"{document.document_id}:{document.version}:{document.content_hash[:12]}", document.document_id, document.model_dump_json(), document.content_hash, "active" if document.active else "inactive", document.previous_version_id))
            cursor.execute("DELETE FROM rag_chunks WHERE document_id=%s", (document.document_id,))
            from ..retrieval.rag import _tokens as rag_tokens
            from ..retrieval.embedding_service import signature as embedding_signature
            for index, (chunk_id, chunk_index, text, chunk_hash) in enumerate(chunks):
                vector = None
                if embeddings and index < len(embeddings):
                    vector = "[" + ",".join(str(value) for value in embeddings[index]) + "]"
                tokens = list(rag_tokens(f"{document.title} {document.publisher} {text}"))
                cursor.execute("INSERT INTO rag_chunks (chunk_id,document_id,chunk_index,text,embedding,embedding_model,content_hash,active,search_tokens) VALUES (%s,%s,%s,%s,%s::vector,%s,%s,%s,%s)", (chunk_id, document.document_id, chunk_index, text, vector, embedding_signature() if vector else None, chunk_hash, document.active, tokens))
        return True
    except Exception as error:
        logger.warning("save_rag_document failed for %s: %s", document.document_id, error)
        return False


ACTIVE_FILTER = "d.active=true AND d.status IN ('active','approved','fetch_failed') AND c.active=true AND (d.effective_from IS NULL OR d.effective_from <= CURRENT_DATE::text) AND (d.effective_until IS NULL OR d.effective_until >= CURRENT_DATE::text)"


def load_rag_chunks() -> list[tuple[RAGDocument, str, str, int]] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute(f"SELECT {DOC_COLUMNS},c.chunk_id,c.text,c.chunk_index FROM rag_documents d JOIN rag_chunks c ON c.document_id=d.document_id WHERE {ACTIVE_FILTER} ORDER BY d.document_id,c.chunk_index")
            return [(_document_from_row(row), row[33], row[34], row[35]) for row in cursor.fetchall()]
    except Exception:
        return None


def fetch_lexical_candidates(query_tokens: list[str], category: Category | None, limit: int) -> list[tuple[RAGDocument, str, str, int]] | None:
    """Small lexical candidate set from PostgreSQL via the search_tokens GIN index.

    Rows are ranked by raw token overlap in SQL; exact scoring/ranking stays in
    the existing Python scorer over this candidate set only. Returns None on DB
    failure (callers degrade honestly), [] when nothing matches."""
    if not query_tokens:
        return []
    try:
        with connection() as conn, conn.cursor() as cursor:
            category_clause = " AND d.category=%s" if category else ""
            params = [list(query_tokens), list(query_tokens)] + ([category] if category else []) + [limit]
            cursor.execute(f"SELECT {DOC_COLUMNS},c.chunk_id,c.text,c.chunk_index, cardinality(ARRAY(SELECT UNNEST(c.search_tokens) INTERSECT SELECT UNNEST(%s::text[]))) AS overlap FROM rag_documents d JOIN rag_chunks c ON c.document_id=d.document_id WHERE {ACTIVE_FILTER} AND c.search_tokens && %s::text[]{category_clause} ORDER BY overlap DESC LIMIT %s", params)
            return [(_document_from_row(row), row[33], row[34], row[35]) for row in cursor.fetchall()]
    except Exception as error:
        logger.warning("Lexical candidate query failed: %s", type(error).__name__)
        return None


def search_rag_vectors(embedding: list[float], limit: int, threshold: float, model: str | None = None) -> list[tuple[RAGDocument, str, str, int, float]] | None:
    try:
        vector = "[" + ",".join(str(value) for value in embedding) + "]"
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute(f"SELECT {DOC_COLUMNS},c.chunk_id,c.text,c.chunk_index,1-(c.embedding <=> %s::vector) AS similarity FROM rag_chunks c JOIN rag_documents d ON d.document_id=c.document_id WHERE {ACTIVE_FILTER} AND c.embedding IS NOT NULL AND c.embedding_model=%s AND 1-(c.embedding <=> %s::vector) >= %s ORDER BY c.embedding <=> %s::vector LIMIT %s", (vector, model or settings.embedding_model, vector, threshold, vector, limit))
            return [(_document_from_row(row), row[33], row[34], row[35], float(row[36])) for row in cursor.fetchall()]
    except Exception:
        return None


def reembed_rag_chunks(embed_texts, tokenizer, signature: str, batch_size: int = 16) -> dict[str, int]:
    """Regenerate embeddings and search_tokens for existing chunks.

    Chunk text, document status, and versions are untouched — only the
    embedding, embedding_model, and search_tokens columns are updated."""
    summary = {"chunks": 0, "embedded": 0, "failed": 0}
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT c.chunk_id, c.text, d.title, d.publisher FROM rag_chunks c JOIN rag_documents d ON d.document_id=c.document_id ORDER BY c.chunk_id")
            rows = cursor.fetchall()
    except Exception as error:
        logger.error("reembed: could not read chunks: %s", error)
        return summary
    summary["chunks"] = len(rows)
    for start in range(0, len(rows), batch_size):
        batch = rows[start:start + batch_size]
        vectors = embed_texts([text for _, text, _, _ in batch])
        try:
            with connection() as conn, conn.cursor() as cursor:
                for index, (chunk_id, text, title, publisher) in enumerate(batch):
                    tokens = tokenizer(f"{title} {publisher} {text}")
                    if vectors and index < len(vectors):
                        vector = "[" + ",".join(str(value) for value in vectors[index]) + "]"
                        cursor.execute("UPDATE rag_chunks SET embedding=%s::vector, embedding_model=%s, search_tokens=%s WHERE chunk_id=%s", (vector, signature, list(tokens), chunk_id))
                        summary["embedded"] += 1
                    else:
                        cursor.execute("UPDATE rag_chunks SET search_tokens=%s WHERE chunk_id=%s", (list(tokens), chunk_id))
                        summary["failed"] += 1
        except Exception as error:
            logger.error("reembed: batch update failed: %s", error)
            summary["failed"] += len(batch)
    return summary


def list_due_rag_documents() -> list[dict[str, str]] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT document_id,title,publisher,category,source_url,content_hash,version,version_id,document_type,language,verified_at,effective_from,original_text FROM rag_documents WHERE active=true AND status IN ('active','approved','fetch_failed') AND (next_check_at IS NULL OR next_check_at <= now()) ORDER BY next_check_at NULLS FIRST")
            return [{"document_id": row[0], "title": row[1], "publisher": row[2], "category": row[3], "source_url": row[4], "content_hash": row[5], "version": row[6], "version_id": row[7] or "", "document_type": row[8] or "guide", "language": row[9], "verified_at": str(row[10]), "effective_from": row[11], "content": row[12]} for row in cursor.fetchall()]
    except Exception:
        return None


def get_rag_document_summary(document_id: str) -> dict[str, str] | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT content_hash,version,version_id,status FROM rag_documents WHERE document_id=%s", (document_id,))
            row = cursor.fetchone()
            return {"content_hash": row[0], "version": row[1], "version_id": row[2] or "", "status": row[3]} if row else None
    except Exception:
        return None


def record_rag_check(document_id: str, *, next_check_at: str, error: str | None = None) -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            if error:
                cursor.execute("UPDATE rag_documents SET last_checked_at=now(), next_check_at=%s, fetch_failures=fetch_failures+1, last_fetch_error=%s, status=CASE WHEN status='active' THEN 'fetch_failed' ELSE status END, updated_at=now() WHERE document_id=%s", (next_check_at, error[:500], document_id))
                action = "fetch_failed"
            else:
                cursor.execute("UPDATE rag_documents SET last_checked_at=now(), next_check_at=%s, fetch_failures=0, last_fetch_error=NULL, status=CASE WHEN status='fetch_failed' THEN 'active' ELSE status END, updated_at=now() WHERE document_id=%s", (next_check_at, document_id))
                action = "checked"
            cursor.execute("INSERT INTO rag_update_audit (document_id,action,detail) VALUES (%s,%s,%s::jsonb)", (document_id, action, json.dumps({"error": error} if error else {})))
        return True
    except Exception:
        return False


def save_pending_rag_version(document: RAGDocument, chunks: list[tuple[str, int, str, str]], embeddings: list[list[float]] | None = None, diff_summary: str = "", quality_score: float | None = None) -> bool:
    """Persist a changed source as review_pending without touching active data."""
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT version_id FROM rag_document_versions WHERE document_id=%s AND content_hash=%s", (document.document_id, document.content_hash))
            if cursor.fetchone():
                return False
            cursor.execute("INSERT INTO rag_document_versions (version_id,document_id,data,content_hash,status,previous_version_id,change_detected_at,crawl_quality_score) VALUES (%s,%s,%s::jsonb,%s,'review_pending',%s,now(),%s)", (document.version_id, document.document_id, document.model_dump_json(), document.content_hash, document.previous_version_id, quality_score))
            for index, (_chunk_id, chunk_index, text, chunk_hash) in enumerate(chunks):
                vector = None
                if embeddings and index < len(embeddings):
                    vector = "[" + ",".join(str(value) for value in embeddings[index]) + "]"
                # Version-prefixed chunk ids: a second pending version of the same
                # document must not collide with earlier version rows (PK chunk_id).
                cursor.execute("INSERT INTO rag_version_chunks (chunk_id,version_id,chunk_index,text,content_hash,embedding,embedding_model) VALUES (%s,%s,%s,%s,%s,%s::vector,%s)", (f"{document.version_id}:{chunk_index}", document.version_id, chunk_index, text, chunk_hash, vector, settings.embedding_model if vector else ""))
            cursor.execute("INSERT INTO rag_update_audit (document_id,version_id,action,detail) VALUES (%s,%s,'change_detected',%s::jsonb)", (document.document_id, document.version_id, json.dumps({"previous_version_id": document.previous_version_id, "new_hash": document.content_hash, "diff_summary": diff_summary[:5000]})))
        return True
    except Exception:
        return False


def save_crawled_document_pending(document: RAGDocument, chunks: list[tuple[str, int, str, str]], quality_score: float | None = None) -> bool:
    """Register a NEW crawled document strictly as review_pending (§15).

    The rag_documents row is created inactive so the document id exists for the
    approval workflow, but ACTIVE_FILTER keeps it invisible to search until an
    administrator approves the pending version. Never overwrites existing rows."""
    document = document.model_copy(update={"active": False, "status": "review_pending"})
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM rag_document_versions WHERE document_id=%s AND content_hash=%s", (document.document_id, document.content_hash))
            if cursor.fetchone():
                return False
            cursor.execute("""INSERT INTO rag_documents (document_id,title,publisher,category,original_text,source_url,language,issued_at,collected_at,verified_at,version,content_hash,active,version_id,source_organization,source_domain,document_type,published_at,promulgated_at,effective_from,effective_until,retrieved_at,last_checked_at,next_check_at,index_version,status,previous_version_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (document_id) DO NOTHING""", (document.document_id, document.title, document.publisher, document.category, document.original_text, document.source_url, document.language, document.issued_at, document.collected_at, document.verified_at, document.version, document.content_hash, False, document.version_id, document.source_organization, document.source_domain, document.document_type, document.published_at, document.promulgated_at, document.effective_from, document.effective_until, document.retrieved_at, document.last_checked_at, document.next_check_at, document.index_version, "review_pending", document.previous_version_id))
            cursor.execute("INSERT INTO rag_document_versions (version_id,document_id,data,content_hash,status,previous_version_id,change_detected_at,crawl_quality_score) VALUES (%s,%s,%s::jsonb,%s,'review_pending',%s,now(),%s) ON CONFLICT (version_id) DO NOTHING", (document.version_id, document.document_id, document.model_dump_json(), document.content_hash, document.previous_version_id, quality_score))
            for _chunk_id, chunk_index, text, chunk_hash in chunks:
                cursor.execute("INSERT INTO rag_version_chunks (chunk_id,version_id,chunk_index,text,content_hash,embedding,embedding_model) VALUES (%s,%s,%s,%s,%s,NULL,'') ON CONFLICT (chunk_id) DO NOTHING", (f"{document.version_id}:{chunk_index}", document.version_id, chunk_index, text, chunk_hash))
            cursor.execute("INSERT INTO rag_update_audit (document_id,version_id,action,detail) VALUES (%s,%s,'crawled',%s::jsonb)", (document.document_id, document.version_id, json.dumps({"source_url": document.source_url, "quality": quality_score})))
        return True
    except Exception as error:
        logger.warning("save_crawled_document_pending failed for %s: %s", document.document_id, error)
        return False


def embed_document_chunks(document_id: str, embed_texts, tokenizer, signature: str) -> dict[str, int]:
    """Post-approval step: fill embeddings and search_tokens for one document's chunks.

    embed_texts may return None (embedding service unavailable -> keep any
    existing vectors, count as failed) or per-item None (policy skip, e.g.
    data-table chunks -> vector is cleared, lexical-only, counted as skipped)."""
    summary = {"chunks": 0, "embedded": 0, "failed": 0, "skipped": 0}
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT c.chunk_id, c.text, d.title, d.publisher FROM rag_chunks c JOIN rag_documents d ON d.document_id=c.document_id WHERE c.document_id=%s ORDER BY c.chunk_index", (document_id,))
            rows = cursor.fetchall()
    except Exception as error:
        logger.error("embed_document_chunks: could not read chunks for %s: %s", document_id, error)
        return summary
    summary["chunks"] = len(rows)
    if not rows:
        return summary
    vectors = None
    try:
        vectors = embed_texts([text for _, text, _, _ in rows])
    except Exception as error:
        logger.warning("embed_document_chunks: embedding failed for %s: %s", document_id, type(error).__name__)
    try:
        with connection() as conn, conn.cursor() as cursor:
            for index, (chunk_id, text, title, publisher) in enumerate(rows):
                tokens = list(tokenizer(f"{title} {publisher} {text}"))
                if vectors and index < len(vectors) and vectors[index] is not None:
                    vector = "[" + ",".join(str(value) for value in vectors[index]) + "]"
                    cursor.execute("UPDATE rag_chunks SET embedding=%s::vector, embedding_model=%s, search_tokens=%s WHERE chunk_id=%s", (vector, signature, tokens, chunk_id))
                    summary["embedded"] += 1
                elif vectors and index < len(vectors):
                    # Policy skip (data-table chunk): lexical-only, clear any stale vector.
                    cursor.execute("UPDATE rag_chunks SET embedding=NULL, embedding_model=NULL, search_tokens=%s WHERE chunk_id=%s", (tokens, chunk_id))
                    summary["skipped"] += 1
                else:
                    cursor.execute("UPDATE rag_chunks SET search_tokens=%s WHERE chunk_id=%s", (tokens, chunk_id))
                    summary["failed"] += 1
    except Exception as error:
        logger.error("embed_document_chunks: update failed for %s: %s", document_id, error)
        summary["failed"] = summary["chunks"] - summary["embedded"]
    return summary


def list_documents_needing_embedding(signature: str) -> list[str] | None:
    """Active documents whose chunks lack an embedding/search_tokens for the given model."""
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT DISTINCT d.document_id FROM rag_documents d JOIN rag_chunks c ON c.document_id=d.document_id WHERE d.active=true AND (c.embedding IS NULL OR c.search_tokens IS NULL OR c.embedding_model IS DISTINCT FROM %s) ORDER BY d.document_id", (signature,))
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return None


def approve_rag_version(version_id: str, reviewed_by: str, review_note: str | None = None) -> str | None:
    """Atomically swap an approved version into the active projection.

    Returns the document_id (truthy) so callers can run the post-approval
    embedding step, or None when the version is missing/already reviewed."""
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT document_id,data FROM rag_document_versions WHERE version_id=%s AND status='review_pending' FOR UPDATE", (version_id,))
            row = cursor.fetchone()
            if not row:
                return None
            document = RAGDocument.model_validate(row[1]).model_copy(update={"status": "active", "active": True, "reviewed_at": date.today().isoformat(), "reviewed_by": reviewed_by, "review_note": review_note})
            cursor.execute("UPDATE rag_document_versions SET status='superseded', reviewed_at=now(), reviewed_by=%s, review_note=%s WHERE document_id=%s AND status='active'", (reviewed_by, review_note, document.document_id))
            cursor.execute("UPDATE rag_document_versions SET status='approved', reviewed_at=now(), reviewed_by=%s, review_note=%s WHERE version_id=%s", (reviewed_by, review_note, version_id))
            cursor.execute("UPDATE rag_documents SET title=%s,publisher=%s,category=%s,original_text=%s,source_url=%s,language=%s,issued_at=%s,collected_at=%s,verified_at=%s,version=%s,content_hash=%s,active=true,version_id=%s,source_organization=%s,source_domain=%s,document_type=%s,published_at=%s,promulgated_at=%s,effective_from=%s,effective_until=%s,retrieved_at=%s,last_checked_at=%s,next_check_at=%s,index_version=%s,status='active',previous_version_id=%s,reviewed_at=now(),reviewed_by=%s,review_note=%s,updated_at=now() WHERE document_id=%s", (document.title, document.publisher, document.category, document.original_text, document.source_url, document.language, document.issued_at, document.collected_at, document.verified_at, document.version, document.content_hash, document.version_id, document.source_organization, document.source_domain, document.document_type, document.published_at, document.promulgated_at, document.effective_from, document.effective_until, document.retrieved_at, document.last_checked_at, document.next_check_at, document.index_version, document.previous_version_id, reviewed_by, review_note, document.document_id))
            cursor.execute("DELETE FROM rag_chunks WHERE document_id=%s", (document.document_id,))
            cursor.execute("INSERT INTO rag_chunks (chunk_id,document_id,chunk_index,text,embedding,embedding_model,content_hash,active) SELECT %s || ':' || chunk_index, %s, chunk_index, text, embedding, embedding_model, content_hash, true FROM rag_version_chunks WHERE version_id=%s", (document.document_id, document.document_id, version_id))
            cursor.execute("UPDATE rag_index_state SET index_version=index_version+1,updated_at=now() WHERE id=true")
            cursor.execute("INSERT INTO rag_update_audit (document_id,version_id,action,detail) VALUES (%s,%s,'approved',%s::jsonb)", (document.document_id, version_id, json.dumps({"reviewed_by": reviewed_by})))
        return document.document_id
    except Exception:
        return None


def reject_rag_version(version_id: str, reviewed_by: str, review_note: str) -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("UPDATE rag_document_versions SET status='inactive',reviewed_at=now(),reviewed_by=%s,review_note=%s WHERE version_id=%s AND status='review_pending'", (reviewed_by, review_note, version_id))
            changed = cursor.rowcount == 1
            if changed:
                cursor.execute("INSERT INTO rag_update_audit (document_id,version_id,action,detail) SELECT document_id,version_id,'rejected',%s::jsonb FROM rag_document_versions WHERE version_id=%s", (json.dumps({"reviewed_by": reviewed_by}), version_id))
            return changed
    except Exception:
        return False


def list_pending_rag_versions() -> list[dict] | None:
    """Review queue for administrators, best quality first (§16).

    crawl_quality_score orders the queue only — approval is always a human action."""
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("""SELECT version_id,document_id,content_hash,created_at,
                data->>'title',data->>'publisher',data->>'source_url',data->>'category',
                substr(data->>'original_text',1,240),crawl_quality_score,previous_version_id,
                data->>'published_at',data->>'last_checked_at'
                FROM rag_document_versions WHERE status='review_pending'
                ORDER BY crawl_quality_score DESC NULLS LAST, created_at""")
            from ..retrieval.rag import is_specific_source_url
            return [{
                "version_id": row[0], "document_id": row[1], "content_hash": row[2], "created_at": str(row[3]),
                "title": row[4], "publisher": row[5], "source_url": row[6], "category": row[7],
                "content_preview": row[8], "crawl_quality_score": float(row[9]) if row[9] is not None else None,
                "is_new_document": row[10] is None, "published_at": row[11], "checked_at": row[12],
                "url_specific": is_specific_source_url(row[6]) if row[6] else False,
            } for row in cursor.fetchall()]
    except Exception:
        return None


def rag_index_version() -> str:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT index_version FROM rag_index_state WHERE id=true")
            row = cursor.fetchone()
            if row:
                return str(row[0])
            cursor.execute("SELECT COALESCE(to_char(max(updated_at), 'YYYYMMDDHH24MISS'), 'memory') FROM rag_documents")
            return str(cursor.fetchone()[0])
    except Exception:
        return settings.rag_index_version


def rag_document_status() -> dict[str, int | str]:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT count(*), count(*) FILTER (WHERE active=true) FROM rag_documents")
            total, active = cursor.fetchone()
            return {"total": total, "active": active, "index_version": rag_index_version()}
    except Exception:
        return {"total": 0, "active": 0, "index_version": settings.rag_index_version}


def save_consultation(response: ConsultationResponse, question_hash: str) -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO consultations (id,question_hash,language,answer_mode,guide_ids,cached) VALUES (%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (id) DO NOTHING", (response.consultation_id, question_hash, response.language, response.answer_mode, json.dumps([guide.id for guide in response.guides]), response.cached))
        return True
    except Exception:
        return False


def save_feedback(feedback: FeedbackRequest) -> bool | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO feedback (consultation_id,rating,reason) VALUES (%s,%s,%s) ON CONFLICT (consultation_id) DO NOTHING RETURNING consultation_id", (feedback.consultation_id, feedback.rating, feedback.reason))
            return cursor.fetchone() is not None
    except Exception:
        return None


def acquire_daily_ai_budget(limit: int) -> bool | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("""INSERT INTO daily_ai_usage (usage_date,calls) VALUES (%s,1) ON CONFLICT (usage_date) DO UPDATE SET calls=daily_ai_usage.calls+1 WHERE daily_ai_usage.calls < %s RETURNING calls""", (date.today(), limit))
            return cursor.fetchone() is not None
    except Exception:
        return None


def database_status() -> OperationsStatus | None:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM consultations")
            consultations = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FILTER (WHERE rating='helpful'), count(*) FILTER (WHERE rating='not_helpful') FROM feedback")
            helpful, not_helpful = cursor.fetchone()
            cursor.execute("SELECT calls FROM daily_ai_usage WHERE usage_date=%s", (date.today(),))
            row = cursor.fetchone()
            return OperationsStatus(consultations=consultations, cache_hits=0, ai_calls=row[0] if row else 0, ai_fallbacks=0, helpful=helpful, not_helpful=not_helpful)
    except Exception:
        return None
