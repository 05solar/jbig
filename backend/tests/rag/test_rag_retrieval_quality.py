# 픽스처 기반 검색 품질(Hit@K·MRR)을 측정·검증하는 테스트 파일
"""Fixture-driven retrieval quality tests: no OpenAI calls, lexical index only.

Metrics (Hit@1/3/5, MRR) are computed over every fixture case that names
expected_document_ids and printed so quality changes are visible in CI output.
"""
import json
import unittest
from pathlib import Path

from app.core.config import settings
from app.chat.consultation import find_guides
from app.retrieval.rag import search_index

FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "rag_cases.json"


def load_cases() -> list[dict]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def document_ranks(query: str) -> list[str]:
    """Ordered unique document ids from the search result (doc-level ranking)."""
    seen: list[str] = []
    for chunk, _ in search_index(query):
        if chunk.document.document_id not in seen:
            seen.append(chunk.document.document_id)
    return seen


class RetrievalQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_key = settings.openai_api_key
        settings.openai_api_key = None
        cls.cases = load_cases()

    @classmethod
    def tearDownClass(cls) -> None:
        settings.openai_api_key = cls.original_key

    def test_fixture_has_required_coverage(self) -> None:
        topics = [case["topic"] for case in self.cases]
        self.assertGreaterEqual(len(self.cases), 30)
        self.assertGreaterEqual(topics.count("stay"), 10)
        self.assertGreaterEqual(topics.count("admin"), 5)
        self.assertGreaterEqual(topics.count("labor"), 10)
        self.assertGreaterEqual(topics.count("out_of_scope"), 5)

    def test_expected_documents_are_retrieved_with_metrics(self) -> None:
        retrieval_cases = [case for case in self.cases if case.get("expected_document_ids")]
        self.assertGreaterEqual(len(retrieval_cases), 15)
        hits = {1: 0, 3: 0, 5: 0}
        reciprocal_ranks: list[float] = []
        for case in retrieval_cases:
            with self.subTest(query=case["query"]):
                ranked = document_ranks(case["query"])
                rank = next((index + 1 for index, document_id in enumerate(ranked) if document_id in case["expected_document_ids"]), None)
                self.assertIsNotNone(rank, f"expected {case['expected_document_ids']} not retrieved; got {ranked}")
                self.assertLessEqual(rank, 5, f"expected document ranked {rank} (>5) for: {case['query']}")
                for k in hits:
                    hits[k] += 1 if rank <= k else 0
                reciprocal_ranks.append(1.0 / rank)
                if case.get("expected_min_score") is not None:
                    best = max(score for chunk, score in search_index(case["query"]) if chunk.document.document_id in case["expected_document_ids"])
                    self.assertGreaterEqual(best, case["expected_min_score"], f"relevance {best} below expected for: {case['query']}")
                if case.get("expected_category"):
                    top_expected = next(chunk for chunk, _ in search_index(case["query"]) if chunk.document.document_id in case["expected_document_ids"])
                    self.assertEqual(top_expected.document.category, case["expected_category"])
        total = len(retrieval_cases)
        metrics = {f"Hit@{k}": round(hits[k] / total, 3) for k in (1, 3, 5)}
        metrics["MRR"] = round(sum(reciprocal_ranks) / total, 3)
        print(f"\n[retrieval metrics over {total} cases] {metrics}")
        self.assertEqual(metrics["Hit@5"], 1.0)
        self.assertGreaterEqual(metrics["Hit@3"], 0.9)
        self.assertGreaterEqual(metrics["Hit@1"], 0.7)
        self.assertGreaterEqual(metrics["MRR"], 0.8)

    def test_expected_guides_are_matched(self) -> None:
        guide_cases = [case for case in self.cases if case.get("expected_guide_ids")]
        self.assertGreaterEqual(len(guide_cases), 8)
        for case in guide_cases:
            with self.subTest(query=case["query"]):
                found = {guide.id for guide in find_guides(case["query"])}
                self.assertTrue(set(case["expected_guide_ids"]) <= found, f"expected {case['expected_guide_ids']}, found {found}")

    def test_out_of_scope_questions_retrieve_nothing(self) -> None:
        for case in self.cases:
            if case["topic"] != "out_of_scope":
                continue
            with self.subTest(query=case["query"]):
                self.assertEqual(search_index(case["query"]), [])
                self.assertEqual(find_guides(case["query"]), [])

    def test_unrelated_documents_do_not_outrank_expected(self) -> None:
        ranked = document_ranks("숙소비를 월급에서 공제했어요")
        self.assertEqual(ranked[0], "moel-wage-deduction-housing")
        self.assertNotIn("hikorea-student-part-time-work", ranked[:3])


if __name__ == "__main__":
    unittest.main()
