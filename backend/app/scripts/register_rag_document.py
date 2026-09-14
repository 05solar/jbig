# 검토 완료 텍스트 파일 1건을 RAG 문서로 등록하는 CLI 파일
"""Register one reviewed text document without fetching a URL."""
import argparse

from ..infra.database import initialize_database, save_rag_document
from ..retrieval.rag import content_hash, register_document


def main() -> None:
    parser = argparse.ArgumentParser(description="Register a reviewed official RAG document")
    parser.add_argument("--id", required=True, dest="document_id")
    parser.add_argument("--title", required=True)
    parser.add_argument("--publisher", required=True)
    parser.add_argument("--category", required=True, choices=("residency", "labor"))
    parser.add_argument("--url", required=True)
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--language", default="ko")
    parser.add_argument("--version", default="1")
    parser.add_argument("--inactive", action="store_true")
    args = parser.parse_args()
    document, chunks = register_document(document_id=args.document_id, title=args.title, publisher=args.publisher, category=args.category, text=open(args.text_file, encoding="utf-8").read(), source_url=args.url, language=args.language, version=args.version, active=not args.inactive)
    if not initialize_database():
        raise SystemExit("PostgreSQL is unavailable")
    saved = save_rag_document(document, [(chunk.chunk_id, chunk.chunk_index, chunk.text, content_hash(chunk.text)) for chunk in chunks])
    print(f"{'saved' if saved else 'unchanged'}: {document.document_id} ({len(chunks)} chunks)")


if __name__ == "__main__":
    main()
