# PostgreSQL 스키마 생성과 시드 데이터 적재 CLI를 제공하는 파일
import sys

from ..infra.database import initialize_database


if __name__ == "__main__":
    if not initialize_database():
        print("PostgreSQL initialization failed. Check DATABASE_URL and Docker.", file=sys.stderr)
        raise SystemExit(1)
    print("PostgreSQL initialized and guide data seeded.")
