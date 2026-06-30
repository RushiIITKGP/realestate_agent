import pytest
from fastapi.testclient import TestClient

from main import app, engine, search_listings, seed_db, Session


@pytest.fixture()
def client():
    seed_db()
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_search_listings():
    seed_db()
    with Session(engine) as db:
        results = search_listings(db, city="Austin", max_price=800000)
    assert results
    assert all(p.city == "Austin" for p in results)


def test_chat_stream_needs_api_key(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    import agent
    import main

    agent.GOOGLE_API_KEY = None
    main.GOOGLE_API_KEY = None

    response = client.post("/chat/stream", json={"session_id": "t1", "message": "hi"})
    assert response.status_code == 503

    agent.GOOGLE_API_KEY = __import__("os").getenv("GOOGLE_API_KEY")
    main.GOOGLE_API_KEY = agent.GOOGLE_API_KEY
