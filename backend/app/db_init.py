import sys

from .database import initialize_database


if __name__ == "__main__":
    if not initialize_database():
        print("PostgreSQL initialization failed. Check DATABASE_URL and Docker.", file=sys.stderr)
        raise SystemExit(1)
    print("PostgreSQL initialized and guide data seeded.")
