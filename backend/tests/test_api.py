import pytest
from fastapi.testclient import TestClient

from fetch_data import rentcast_to_row
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


def test_rentcast_to_row():
    row = rentcast_to_row(
        {
            "id": "3821-Hargis-St,-Austin,-TX-78723",
            "addressLine1": "3821 Hargis St",
            "city": "Austin",
            "state": "TX",
            "zipCode": "78723",
            "county": "Travis",
            "propertyType": "Single Family",
            "bedrooms": 4,
            "bathrooms": 2.5,
            "squareFootage": 2345,
            "yearBuilt": 2008,
            "price": 899000,
            "status": "Active",
            "daysOnMarket": 10,
        }
    )
    assert row["city"] == "Austin"
    assert row["price"] == 899000
    assert row["beds"] == 4


def test_import_listings_endpoint(client, monkeypatch):
    sample = [
        {
            "id": "test-listing-1",
            "addressLine1": "100 Test St",
            "city": "Austin",
            "state": "TX",
            "zipCode": "78701",
            "propertyType": "Condo",
            "bedrooms": 2,
            "bathrooms": 2,
            "squareFootage": 900,
            "yearBuilt": 2010,
            "price": 500000,
            "status": "Active",
        }
    ]

    monkeypatch.setattr("fetch_data.fetch_sale_listings", lambda city, state, limit: sample)

    response = client.post("/listings/import", params={"city": "Austin", "state": "TX", "limit": 1})
    assert response.status_code == 200
    assert response.json()["message"] == "Imported 1 listings"

    with Session(engine) as db:
        results = search_listings(db, city="Austin")
    assert len(results) == 1
    assert results[0].address == "100 Test St"


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
