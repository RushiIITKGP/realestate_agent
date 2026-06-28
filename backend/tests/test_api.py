import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import create_app
from app.seed.seed import seed_database


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


def test_list_properties_filter_by_city(client):
    response = client.get("/properties", params={"city": "Austin", "max_price": 800000})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(item["city"] == "Austin" for item in data)
    assert all(item["price"] <= 800000 for item in data)


def test_get_property_details(client):
    response = client.get("/properties/prop-003")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "prop-003"
    assert data["city"] == "Austin"


def test_property_keyword_search(client):
    response = client.get("/properties", params={"city": "Austin", "keywords": "garage"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_chat_requires_openai_key(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    response = client.post(
        "/chat",
        json={"session_id": "test-session", "message": "homes in Austin"},
    )
    assert response.status_code == 503

    get_settings.cache_clear()
