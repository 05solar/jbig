# 공식 문서 색인과 임베딩 재생성(--reembed) CLI를 제공하는 파일
import argparse

from ..retrieval import embedding_service
from ..infra.database import initialize_database, reembed_rag_chunks
from ..retrieval.rag import _tokens, index_documents


def main() -> None:
    parser = argparse.ArgumentParser(description="Index or re-embed reviewed official RAG documents")
    parser.add_argument("--reembed", action="store_true", help="Regenerate embeddings and search tokens for existing chunks without touching text/status/versions")
    args = parser.parse_args()
    if not initialize_database():
        raise SystemExit(
            "PostgreSQL is unavailable. Start the pgvector database first "
            "(docker compose up -d db), check DATABASE_URL, then retry. "
            "The running API can still use in-memory sample documents, "
            "but they are not persisted by this command."
        )
    try:
        embedding_service.verify_dimension()
    except RuntimeError as error:
        raise SystemExit(str(error))
    if args.reembed:
        summary = reembed_rag_chunks(embedding_service.embed_texts, lambda text: _tokens(text), embedding_service.signature())
        print(f"chunks: {summary['chunks']}, embedded: {summary['embedded']}, failed: {summary['failed']}, provider: {embedding_service.signature()}, dimension: {embedding_service.dimension()}")
        return
    indexed, skipped = index_documents()
    print(f"RAG documents indexed: {indexed}, unchanged or skipped: {skipped}")


if __name__ == "__main__":
    main()
