# RAG 운영 CLI(원문 변경 확인·검토 대기 조회·버전 승인/거절)를 제공하는 파일
import argparse
import json

from ..infra.database import approve_rag_version, initialize_database, list_pending_rag_versions, reject_rag_version
from ..retrieval.rag import index_approved_document
from ..retrieval.updates import check_source_updates


def main() -> None:
    parser = argparse.ArgumentParser(description="JB Bridge stored-RAG maintenance")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check-source-updates")
    sub.add_parser("list-pending-updates")
    approve = sub.add_parser("approve-document-version")
    approve.add_argument("version_id")
    approve.add_argument("--reviewed-by", required=True)
    approve.add_argument("--note", default="")
    reject = sub.add_parser("reject-document-version")
    reject.add_argument("version_id")
    reject.add_argument("--reviewed-by", required=True)
    reject.add_argument("--note", required=True)
    args = parser.parse_args()
    if not initialize_database():
        raise SystemExit("PostgreSQL is unavailable")
    if args.command == "check-source-updates":
        print(json.dumps(check_source_updates(), ensure_ascii=False))
    elif args.command == "list-pending-updates":
        print(json.dumps(list_pending_rag_versions() or [], ensure_ascii=False, indent=2))
    elif args.command == "approve-document-version":
        document_id = approve_rag_version(args.version_id, args.reviewed_by, args.note)
        if document_id:
            embedding = index_approved_document(document_id)
            print(json.dumps({"approved": True, "document_id": document_id, "embedding": embedding}, ensure_ascii=False))
        else:
            print("not found or already reviewed")
    elif args.command == "reject-document-version":
        print("rejected" if reject_rag_version(args.version_id, args.reviewed_by, args.note) else "not found or already reviewed")


if __name__ == "__main__":
    main()
