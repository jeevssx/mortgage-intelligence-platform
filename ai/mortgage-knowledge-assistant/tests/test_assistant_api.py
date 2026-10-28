from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.config import Settings
from src.generation.llm_client import ExtractiveLlmClient
from src.retrieval.embeddings import TfidfEmbeddingBackend
from src.retrieval.vector_store import VectorStore

REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = REPO_ROOT / "knowledge" / "v1"


@pytest.fixture(scope="module")
def real_store() -> VectorStore:
    return VectorStore.build(KNOWLEDGE_DIR, TfidfEmbeddingBackend(), size_words=400, overlap_words=50)


@pytest.fixture
def client(real_store: VectorStore) -> TestClient:
    settings = Settings(similarity_threshold=0.15, top_k=5)
    app = create_app(settings, store=real_store, llm_client=ExtractiveLlmClient())
    return TestClient(app)


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "UP"


def test_ask_relevant_question_returns_answer_with_citation(client: TestClient):
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "What happens when a payment is 30 days late?"},
        headers={"X-Correlation-Id": "test-ask-001"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["citations"], "expected at least one citation"
    assert body["citations"][0]["documentId"] == "delinquency-playbook.md"
    assert body["confidence"] >= 0.15
    assert body["requiresHumanApproval"] is False
    assert body["correlationId"] == "test-ask-001"
    assert body["answer"]


def test_ask_off_topic_question_returns_insufficient_context(client: TestClient):
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "What is the weather forecast for tomorrow?"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["citations"] == []
    assert body["requiresHumanApproval"] is True
    assert "insufficient" in body["answer"].lower() or "don't have reliable information" in body["answer"]


def test_ask_decision_question_flags_human_approval_even_with_good_retrieval(client: TestClient):
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Can a servicing agent approve a loan modification?"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["citations"], "expected citations — this question has strong corpus coverage"
    assert body["requiresHumanApproval"] is True


def test_ask_validates_empty_question(client: TestClient):
    response = client.post("/api/v1/assistant/ask", json={"question": ""})
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_summarize_incident(client: TestClient):
    incident_text = (REPO_ROOT / "incidents" / "sample-incident-001.md").read_text()
    response = client.post("/api/v1/assistant/summarize-incident", json={"incidentText": incident_text})
    body = response.json()

    assert response.status_code == 200
    assert body["summary"]
    assert body["recommendedRunbookLinks"]
    assert body["requiresHumanApproval"] is False  # this sample incident documents root cause + resolution


def test_auth_required_when_jwt_secret_configured(real_store: VectorStore):
    settings = Settings(jwt_secret="test-secret-at-least-32-bytes-long-xx")
    app = create_app(settings, store=real_store, llm_client=ExtractiveLlmClient())
    client = TestClient(app)

    unauthenticated = client.post("/api/v1/assistant/ask", json={"question": "anything"})
    assert unauthenticated.status_code == 401

    token = jwt.encode({"sub": "test-user"}, settings.jwt_secret, algorithm="HS256")
    authenticated = client.post(
        "/api/v1/assistant/ask",
        json={"question": "What happens when a payment is 30 days late?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert authenticated.status_code == 200
