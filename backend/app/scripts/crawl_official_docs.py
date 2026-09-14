# 공식문서 크롤링 CLI(탐색 dry-run·review_pending 등록·승인 문서 색인)를 제공하는 파일
"""CLI for the official-document crawler.

Modes (§20):
  --dry-run              explore and print candidates only; nothing is written
  (default / --review)   register candidates as review_pending; no embedding
  --approved-only-index  embed+tokenize chunks of already-approved documents

Examples:
  python -m app.scripts.crawl_official_docs --dry-run --domain moel.go.kr --limit 20
  python -m app.scripts.crawl_official_docs --category labor --limit 30
  python -m app.scripts.crawl_official_docs --approved-only-index
"""
import argparse
import json

from ..core.config import settings
from ..crawler import run_crawl, sources_for
from ..infra.database import initialize_database, list_documents_needing_embedding
from ..retrieval.rag import index_approved_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Selective official-document crawler (review_pending only)")
    parser.add_argument("--domain", help="restrict to one domain, e.g. moel.go.kr")
    parser.add_argument("--category", choices=("residency", "labor"), help="restrict to one category")
    parser.add_argument("--limit", type=int, default=None, help="max detail pages per source (default CRAWLER_MAX_DETAIL_PAGES)")
    parser.add_argument("--since", help="skip documents published before YYYY-MM-DD (when a date is detected)")
    parser.add_argument("--dry-run", action="store_true", help="explore only; do not write to the database")
    parser.add_argument("--review", action="store_true", help="register candidates as review_pending (default mode)")
    parser.add_argument("--approved-only-index", action="store_true", help="embed chunks of approved documents; no crawling")
    args = parser.parse_args()

    if args.approved_only_index:
        if not initialize_database():
            raise SystemExit("PostgreSQL is unavailable")
        from ..retrieval import embedding_service
        pending = list_documents_needing_embedding(embedding_service.signature()) or []
        results = {document_id: index_approved_document(document_id) for document_id in pending}
        print(json.dumps({"documents": len(results), "results": results}, ensure_ascii=False, indent=2))
        return

    specs = sources_for(args.domain, args.category)
    if not specs:
        raise SystemExit(f"No source spec matches domain={args.domain} category={args.category}")
    if not args.dry_run and not initialize_database():
        raise SystemExit("PostgreSQL is unavailable (use --dry-run to explore without a database)")
    report, candidates = run_crawl(specs, limit=args.limit, dry_run=args.dry_run, since=args.since)
    output = {"mode": "dry-run" if args.dry_run else "review", "sources": [spec.key for spec in specs], "report": report.as_dict()}
    if args.dry_run:
        output["candidates"] = [{
            "url": candidate.canonical_url, "title": candidate.title, "quality": candidate.quality,
            "category": candidate.spec.category, "language": candidate.language,
            "published_at": candidate.published_at, "chars": len(candidate.body),
        } for candidate in candidates]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
