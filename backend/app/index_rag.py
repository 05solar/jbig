from .database import initialize_database
from .rag import index_documents


if __name__ == "__main__":
    if not initialize_database():
        raise SystemExit(
            "PostgreSQL is unavailable. Start the pgvector database first "
            "(docker compose up -d db), check DATABASE_URL, then retry. "
            "The running API can still use in-memory sample documents, "
            "but they are not persisted by this command."
        )
    indexed, skipped = index_documents()
    print(f"RAG documents indexed: {indexed}, unchanged or skipped: {skipped}")
