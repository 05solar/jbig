from .database import initialize_database
from .embeddings import index_guides


if __name__ == "__main__":
    if not initialize_database():
        raise SystemExit("PostgreSQL is unavailable.")
    indexed, failed = index_guides()
    print(f"Guide embeddings indexed: {indexed}, failed or skipped: {failed}")
