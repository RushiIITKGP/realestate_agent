import pytest
from fastapi.testclient import TestClient

from fetch_data import market_to_neighborhood, rentcast_to_row
from main import app, engine, search_listings, seed_db, Session, get_neighborhood


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


def test_rentcast_to_row_with_walk_score():
    row = rentcast_to_row(
        {
            "id": "3821-Hargis-St,-Austin,-TX-78723",
            "addressLine1": "3821 Hargis St",
            "formattedAddress": "3821 Hargis St, Austin, TX 78723",
            "city": "Austin",
            "state": "TX",
            "zipCode": "78723",
            "propertyType": "Single Family",
            "bedrooms": 4,
            "bathrooms": 2.5,
            "squareFootage": 2345,
            "yearBuilt": 2008,
            "price": 899000,
            "status": "Active",
            "latitude": 30.29,
            "longitude": -97.70,
        },
        walk_score=82,
    )
    assert row["walk_score"] == 82
    assert row["neighborhood"] == "78723"
    assert "Walk Score 82" in row["description"]


def test_market_to_neighborhood():
    hood = market_to_neighborhood(
        {
            "zipCode": "78723",
            "saleData": {
                "medianPrice": 650000,
                "averageDaysOnMarket": 45,
                "totalListings": 120,
                "averagePricePerSquareFoot": 320,
                "dataByPropertyType": [{"propertyType": "Single Family", "medianPrice": 700000}],
            },
        },
        "Austin",
        "TX",
        avg_walk=78,
    )
    assert hood["name"] == "78723"
    assert hood["median_price"] == 650000
    assert hood["walk_score"] == 78
    assert "78723" in hood["summary"]


def test_import_listings_endpoint(client, monkeypatch):
    sample = [
        {
            "id": "test-listing-1",
            "addressLine1": "100 Test St",
            "formattedAddress": "100 Test St, Austin, TX 78701",
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
            "latitude": 30.27,
            "longitude": -97.74,
        }
    ]

    monkeypatch.setattr("fetch_data.fetch_sale_listings", lambda city, state, limit: sample)
    monkeypatch.setattr("fetch_data.fetch_walk_score", lambda address, lat, lon, cache: 85)
    monkeypatch.setattr(
        "fetch_data.fetch_market_stats",
        lambda zip_code: {
            "zipCode": zip_code,
            "saleData": {"medianPrice": 550000, "averageDaysOnMarket": 30, "totalListings": 50},
        },
    )

    response = client.post("/listings/import", params={"city": "Austin", "state": "TX", "limit": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Imported 1 listings"
    assert body["neighborhoods"] == 1
    assert body["walk_scores"] == 1

    with Session(engine) as db:
        results = search_listings(db, city="Austin")
        hood = get_neighborhood(db, "78701", "Austin")
    assert len(results) == 1
    assert results[0].walk_score == 85
    assert hood is not None
    assert hood.median_price == 550000


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
