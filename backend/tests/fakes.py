# 테스트용 결정적 가짜 구현(가짜 임베딩·FakeLLMClient·FailingLLMClient)을 제공하는 파일
"""Deterministic fakes so RAG tests never call external APIs.

Every fake mirrors the small slice of the OpenAI client surface the app uses
(client.responses.create / client.embeddings.create) and is fully repeatable:
the same input always produces the same output.
"""
import hashlib


def fake_embedding(text: str, dimensions: int = 16) -> list[float]:
    """Deterministic pseudo-embedding derived from a content hash."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [round((byte / 255.0) * 2 - 1, 6) for byte in digest[:dimensions]]


def fake_create_embeddings(texts: list[str], client_factory=None) -> list[list[float]]:
    """Drop-in replacement for app.retrieval.embeddings.create_embeddings."""
    return [fake_embedding(text) for text in texts]


class FakeEmbeddingsAPI:
    last_input = None

    def create(self, **kwargs):
        FakeEmbeddingsAPI.last_input = kwargs["input"]
        data = [type("Embedding", (), {"index": index, "embedding": fake_embedding(text)})() for index, text in enumerate(kwargs["input"])]
        return type("Response", (), {"data": data})()


class FakeLLMResponses:
    """Records the request and returns a configurable deterministic answer."""

    output_text = "공식 자료에 따라 관할 기관에 확인하세요."

    def __init__(self) -> None:
        self.params = None

    def create(self, **kwargs):
        self.params = kwargs
        FakeLLMClient.last_params = kwargs
        return type("Response", (), {"output_text": FakeLLMResponses.output_text})()


class FakeLLMClient:
    """Stands in for openai.OpenAI: responses + embeddings, no network."""

    last_instance = None
    last_params = None

    def __init__(self, **kwargs) -> None:
        self.responses = FakeLLMResponses()
        self.embeddings = FakeEmbeddingsAPI()
        FakeLLMClient.last_instance = self


class FailingLLMClient:
    """Simulates a network/API failure at client construction time."""

    def __init__(self, **kwargs) -> None:
        raise RuntimeError("simulated OpenAI outage")
