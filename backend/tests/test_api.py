import pytest
from fastapi.testclient import TestClient

from main import (
    Session,
    app,
    engine,
    get_neighborhood,
    import_listings,
    market_to_neighborhood,
    rentcast_to_row,
    search_listings,
    search_similar_listings,
)

SAMPLE_LISTING = {
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
}

SAMPLE_HOUSE = {
    **SAMPLE_LISTING,
    "id": "test-listing-2",
    "addressLine1": "200 Oak Ave",
    "formattedAddress": "200 Oak Ave, Austin, TX 78702",
    "zipCode": "78702",
    "propertyType": "Single Family",
    "bedrooms": 4,
    "price": 750000,
}


def _fake_embed(texts):
    vectors = []
    for text in texts:
        lower = text.lower()
        if "condo" in lower:
            vectors.append([1.0, 0.0, 0.0])
        elif "single family" in lower:
            vectors.append([0.9, 0.1, 0.0])
        else:
            vectors.append([0.0, 1.0, 0.0])
    return vectors


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _import_sample(monkeypatch, listings=None):
    listings = listings or [SAMPLE_LISTING]
    monkeypatch.setattr("main.fetch_sale_listings", lambda city, state, limit: listings)
    monkeypatch.setattr(
        "main.fetch_market_stats",
        lambda zip_code: {
            "zipCode": zip_code,
            "saleData": {"medianPrice": 550000, "averageDaysOnMarket": 30, "totalListings": 50},
        },
    )
    monkeypatch.setattr("main.embed_texts", _fake_embed)
    monkeypatch.setattr("main.GOOGLE_API_KEY", "test-key")
    return import_listings("Austin", "TX", limit=len(listings))


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_rentcast_to_row():
    row = rentcast_to_row(
        {
            **SAMPLE_LISTING,
            "id": "3821-Hargis-St,-Austin,-TX-78723",
            "addressLine1": "3821 Hargis St",
            "formattedAddress": "3821 Hargis St, Austin, TX 78723",
            "zipCode": "78723",
            "propertyType": "Single Family",
            "bedrooms": 4,
            "bathrooms": 2.5,
            "squareFootage": 2345,
            "daysOnMarket": 12,
            "price": 899000,
        }
    )
    assert row["neighborhood"] == "78723"
    assert row["beds"] == 4
    assert "12 days on market" in row["description"]


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
    )
    assert hood["name"] == "78723"
    assert hood["median_price"] == 650000
    assert "78723" in hood["summary"]


def test_search_listings(monkeypatch):
    _import_sample(monkeypatch)
    with Session(engine) as db:
        results = search_listings(db, city="Austin", max_price=800000)
    assert len(results) == 1
    assert results[0].city == "Austin"


def test_similar_listings(monkeypatch):
    _import_sample(monkeypatch, listings=[SAMPLE_LISTING, SAMPLE_HOUSE])
    with Session(engine) as db:
        similar = search_similar_listings(db, "test-listing-1", limit=3)
    assert len(similar) == 1
    assert similar[0].id == "test-listing-2"


def test_import_listings_endpoint(client, monkeypatch):
    monkeypatch.setattr("main.fetch_sale_listings", lambda city, state, limit: [SAMPLE_LISTING])
    monkeypatch.setattr(
        "main.fetch_market_stats",
        lambda zip_code: {
            "zipCode": zip_code,
            "saleData": {"medianPrice": 550000, "averageDaysOnMarket": 30, "totalListings": 50},
        },
    )
    monkeypatch.setattr("main.embed_texts", _fake_embed)
    monkeypatch.setattr("main.GOOGLE_API_KEY", "test-key")

    response = client.post("/listings/import", params={"city": "Austin", "state": "TX", "limit": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["message"] == "Imported 1 listings"
    assert body["neighborhoods"] == 1
    assert body["embedded"] == 1

    with Session(engine) as db:
        results = search_listings(db, city="Austin")
        hood = get_neighborhood(db, "78701", "Austin")
    assert len(results) == 1
    assert results[0].price == 500000
    assert results[0].embedding is not None
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
