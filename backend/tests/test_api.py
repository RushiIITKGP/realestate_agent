import pytest
from fastapi.testclient import TestClient

from app.agent import _message_text
from app.db import SessionLocal, init_db
from app.main import create_app
from app.schemas import PropertySearchParams
from app import search as listing_search
from app.seed import seed_database


@pytest.fixture()
def client():
    init_db()
    with SessionLocal() as db:
        seed_database(db)

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_message_text_from_gemini_blocks():
    content = [{"type": "text", "text": "Hello from Gemini.", "extras": {"signature": "abc"}}]
    assert _message_text(content) == "Hello from Gemini."


def test_semantic_search_with_embeddings(monkeypatch):
    init_db()
    with SessionLocal() as db:
        seed_database(db)
        props = listing_search.get_by_ids(db, ["prop-003", "prop-004"])
        props[0].embedding = [1.0, 0.0, 0.0]
        props[1].embedding = [0.0, 1.0, 0.0]
        db.commit()

    monkeypatch.setattr(
        "app.search.embed_text",
        lambda text: [1.0, 0.0, 0.0] if "zilker" in text.lower() else [0.5, 0.5, 0.0],
    )

    with SessionLocal() as db:
        results = listing_search.search(
            db,
            PropertySearchParams(city="Austin", semantic_query="cozy home in Zilker"),
        )
    assert len(results) >= 1
    assert results[0].id == "prop-003"


def test_find_similar_properties():
    init_db()
    with SessionLocal() as db:
        seed_database(db)
        props = listing_search.get_by_ids(db, ["prop-003", "prop-004"])
        props[0].embedding = [1.0, 0.0, 0.0]
        props[1].embedding = [0.9, 0.1, 0.0]
        db.commit()

        similar = listing_search.find_similar(db, "prop-003", limit=3)
    assert len(similar) >= 1
    assert similar[0].id == "prop-004"


def test_chat_requires_google_api_key(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    response = client.post(
        "/chat",
        json={"session_id": "test-session", "message": "homes in Austin"},
    )
    assert response.status_code == 503

    get_settings.cache_clear()
