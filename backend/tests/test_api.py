import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal, init_db
from app.main import create_app
from app.models import Property
from app.seed.seed import seed_database
from app.services import properties as property_db
from app.schemas.property import PropertySearchParams


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


def test_semantic_search_with_embeddings(client, monkeypatch):
    init_db()
    with SessionLocal() as db:
        seed_database(db)
        props = property_db.get_by_ids(db, ["prop-003", "prop-004"])
        props[0].embedding = [1.0, 0.0, 0.0]
        props[1].embedding = [0.0, 1.0, 0.0]
        db.commit()

    monkeypatch.setattr(
        "app.services.embeddings.embed_text",
        lambda text: [1.0, 0.0, 0.0] if "zilker" in text.lower() else [0.5, 0.5, 0.0],
    )

    with SessionLocal() as db:
        results = property_db.search(
            db,
            PropertySearchParams(city="Austin", semantic_query="cozy home in Zilker"),
        )
    assert len(results) >= 1
    assert results[0].id == "prop-003"


def test_find_similar_properties(client):
    init_db()
    with SessionLocal() as db:
        seed_database(db)
        props = property_db.get_by_ids(db, ["prop-003", "prop-004"])
        props[0].embedding = [1.0, 0.0, 0.0]
        props[1].embedding = [0.9, 0.1, 0.0]
        db.commit()

        similar = property_db.find_similar(db, "prop-003", limit=3)
    assert len(similar) >= 1
    assert similar[0].id == "prop-004"


def test_similar_endpoint(client):
    init_db()
    with SessionLocal() as db:
        seed_database(db)
        prop = property_db.get_by_id(db, "prop-003")
        prop.embedding = [1.0, 0.0, 0.0]
        other = property_db.get_by_id(db, "prop-004")
        other.embedding = [0.9, 0.1, 0.0]
        db.commit()

    response = client.get("/properties/prop-003/similar")
    assert response.status_code == 200
    assert len(response.json()) >= 1


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
