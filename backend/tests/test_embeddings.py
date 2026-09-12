import unittest
from unittest.mock import patch

from app.config import settings
from app.data import GUIDES
from app.embeddings import guide_embedding_text, index_guides, search_guides_semantically


class FakeEmbeddings:
    last_input = None

    def create(self, **kwargs):
        FakeEmbeddings.last_input = kwargs["input"]
        data = [type("Embedding", (), {"index": index, "embedding": [0.1, 0.2, 0.3]})() for index, _ in enumerate(kwargs["input"])]
        return type("Response", (), {"data": data})()


class FakeClient:
    def __init__(self, **kwargs) -> None:
        self.embeddings = FakeEmbeddings()


class EmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = settings.openai_api_key
        settings.openai_api_key = "test-key"

    def tearDown(self) -> None:
        settings.openai_api_key = self.original_key

    def test_search_document_contains_all_languages(self) -> None:
        text = guide_embedding_text(GUIDES[0])
        self.assertIn(GUIDES[0].title["ko"], text)
        self.assertIn(GUIDES[0].title["en"], text)
        self.assertIn(GUIDES[0].title["vi"], text)

    @patch("app.embeddings.acquire_ai_budget", return_value=True)
    def test_semantic_search_redacts_and_returns_database_matches(self, _budget) -> None:
        captured = {}
        def searcher(vector, limit, threshold):
            captured.update(vector=vector, limit=limit, threshold=threshold)
            return [(next(guide for guide in GUIDES if guide.id == "unpaid-wages"), 0.88)]
        result = search_guides_semantically("번호 900101-1234567 사장님이 돈을 미뤄요", FakeClient, searcher)
        self.assertEqual(result[0].id, "unpaid-wages")
        self.assertNotIn("900101-1234567", FakeEmbeddings.last_input[0])
        self.assertEqual(captured["limit"], 3)
        self.assertEqual(captured["threshold"], settings.vector_similarity_threshold)

    @patch("app.embeddings.acquire_ai_budget", return_value=True)
    @patch("app.embeddings.save_guide_embedding", return_value=True)
    @patch("app.embeddings.embedding_hashes", return_value={})
    @patch("app.embeddings.database_available", return_value=True)
    def test_indexer_batches_and_saves_all_changed_guides(self, _available, _hashes, _save, _budget) -> None:
        indexed, failed = index_guides(FakeClient)
        self.assertEqual(indexed, len(GUIDES))
        self.assertEqual(failed, 0)
        self.assertEqual(len(FakeEmbeddings.last_input), len(GUIDES))


if __name__ == "__main__":
    unittest.main()
