# 선택적 실제 OpenAI API 스모크(기본 skip)를 수행하는 테스트 파일
"""Optional real-API smoke test. SKIPPED by default.

Run explicitly with:  RAG_SMOKE_REAL_API=1 python -m unittest tests.test_smoke_real_api
Budget: at most 1 embedding call and 2 LLM calls. Requires OPENAI_API_KEY.
"""
import os
import unittest

from app.core.config import settings

RUN_SMOKE = os.environ.get("RAG_SMOKE_REAL_API") == "1" and bool(settings.openai_api_key)


@unittest.skipUnless(RUN_SMOKE, "real API smoke test disabled (set RAG_SMOKE_REAL_API=1 with OPENAI_API_KEY)")
class RealApiSmokeTests(unittest.TestCase):
    def test_embedding_api_once(self) -> None:
        from app.retrieval.embeddings import create_embeddings
        vectors = create_embeddings(["체류기간 연장 신청"])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), settings.embedding_dimensions)

    def test_llm_rag_answer_and_refusal(self) -> None:
        from app.chat.ai_consultation import generate_rag_answer
        from app.retrieval.rag import search_official_documents
        from app.core.schemas import ConsultationResponse
        empty = ConsultationResponse(language="ko", message="", guide=None, guides=[], agencies=[])
        # Lexical-only retrieval keeps the embedding budget at the single call above.
        grounded = generate_rag_answer(empty, "월급을 받지 못했어요", search_official_documents("월급을 받지 못했어요"))
        self.assertEqual(grounded.answer_mode, "rag")
        self.assertTrue(grounded.sources)
        refused = generate_rag_answer(empty, "오늘 전주 날씨 알려줘", search_official_documents("오늘 전주 날씨 알려줘"))
        self.assertEqual(refused.answer_mode, "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
