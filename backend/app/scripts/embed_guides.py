# 가이드 임베딩 생성/재생성(--reembed) CLI를 제공하는 파일
import argparse

from ..retrieval import embedding_service
from ..infra.database import initialize_database
from ..retrieval.embeddings import index_guides

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed guides through the shared embedding provider")
    parser.add_argument("--reembed", action="store_true", help="Regenerate every guide embedding with the current provider, ignoring content hashes")
    args = parser.parse_args()
    if not initialize_database():
        raise SystemExit("PostgreSQL is unavailable.")
    try:
        embedding_service.verify_dimension()
    except RuntimeError as error:
        raise SystemExit(str(error))
    indexed, failed = index_guides(force=args.reembed)
    print(f"Guide embeddings indexed: {indexed}, failed or skipped: {failed}, provider: {embedding_service.signature()}, dimension: {embedding_service.dimension()}")
