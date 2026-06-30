"""Fetch real listings and zip market stats from RentCast."""

import os
import sys

import httpx
from dotenv import load_dotenv
from sqlalchemy import delete
from sqlalchemy.orm import Session

load_dotenv()

RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")
LISTINGS_URL = "https://api.rentcast.io/v1/listings/sale"
MARKETS_URL = "https://api.rentcast.io/v1/markets"


def _property_type(raw: str | None) -> str:
    value = (raw or "").lower()
    if "condo" in value:
        return "condo"
    if "town" in value:
        return "townhouse"
    return "house"


def fetch_market_stats(zip_code: str) -> dict | None:
    if not RENTCAST_API_KEY:
        return None

    response = httpx.get(
        MARKETS_URL,
        params={"zipCode": zip_code, "dataType": "Sale"},
        headers={"X-Api-Key": RENTCAST_API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()


def market_to_neighborhood(market: dict, city: str, state: str) -> dict:
    zip_code = market.get("zipCode") or market.get("id") or ""
    sale = market.get("saleData") or {}
    median = int(sale.get("medianPrice") or 0)
    avg_dom = sale.get("averageDaysOnMarket")
    total = sale.get("totalListings")
    avg_ppsf = sale.get("averagePricePerSquareFoot")

    summary = f"ZIP {zip_code} market in {city}, {state}. Median list price ${median:,}."
    if avg_dom is not None:
        summary += f" Average {avg_dom:.0f} days on market."
    if total is not None:
        summary += f" {total} active listings in this zip."

    highlights = []
    if avg_ppsf:
        highlights.append(f"${avg_ppsf:.0f}/sqft average")
    for row in (sale.get("dataByPropertyType") or [])[:3]:
        median_type = row.get("medianPrice")
        if median_type:
            highlights.append(f"{row.get('propertyType')}: ${int(median_type):,} median")

    return {
        "id": f"zip-{zip_code}",
        "name": zip_code,
        "city": city,
        "state": state,
        "summary": summary,
        "median_price": median,
        "highlights": highlights,
    }


def rentcast_to_row(item: dict) -> dict:
    beds = int(item.get("bedrooms") or 0)
    baths = float(item.get("bathrooms") or 0)
    sqft = int(item.get("squareFootage") or 0)
    price = int(item.get("price") or 0)
    city = item.get("city") or ""
    state = item.get("state") or ""
    zip_code = item.get("zipCode") or ""
    prop_type = item.get("propertyType") or "Home"

    description = (
        f"{prop_type} for sale in {city}, {state}. "
        f"{beds} bedrooms, {baths} baths, {sqft:,} sqft. "
        f"Listed at ${price:,}."
    )
    if item.get("daysOnMarket"):
        description += f" {item['daysOnMarket']} days on market."

    features = [prop_type]
    if item.get("lotSize"):
        features.append(f"lot {item['lotSize']:,} sqft")
    if item.get("yearBuilt"):
        features.append(f"built {item['yearBuilt']}")

    return {
        "id": item["id"],
        "address": item.get("addressLine1") or item.get("formattedAddress") or "Unknown",
        "city": city,
        "state": state,
        "zip": zip_code,
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "property_type": _property_type(prop_type),
        "year_built": int(item.get("yearBuilt") or 0),
        "description": description,
        "features": features,
        "neighborhood": zip_code or item.get("county") or "Area",
        "status": "for_sale",
    }


def fetch_sale_listings(city: str, state: str, limit: int = 20) -> list[dict]:
    if not RENTCAST_API_KEY:
        raise ValueError("Set RENTCAST_API_KEY in backend/.env (free key at https://rentcast.io)")

    response = httpx.get(
        LISTINGS_URL,
        params={"city": city, "state": state, "status": "Active", "limit": limit},
        headers={"X-Api-Key": RENTCAST_API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"Unexpected RentCast response: {data}")
    return data


def import_listings(city: str, state: str, limit: int = 20, replace: bool = True) -> dict:
    from main import Neighborhood, Property, engine

    listings = fetch_sale_listings(city, state, limit)
    rows = [rentcast_to_row(item) for item in listings]

    zip_meta: dict[str, tuple[str, str]] = {}
    for item in listings:
        z = item.get("zipCode")
        if z:
            zip_meta[z] = (item.get("city") or city, item.get("state") or state)

    markets: dict[str, dict] = {}
    for zip_code, (zip_city, zip_state) in zip_meta.items():
        try:
            market = fetch_market_stats(zip_code)
            if market:
                markets[zip_code] = market
        except httpx.HTTPError:
            continue

    with Session(engine) as db:
        if replace:
            db.execute(delete(Property))
            db.execute(delete(Neighborhood))

        for row in rows:
            db.merge(Property(**row))

        for zip_code, market in markets.items():
            zip_city, zip_state = zip_meta[zip_code]
            db.merge(Neighborhood(**market_to_neighborhood(market, zip_city, zip_state)))

        db.commit()

    return {"listings": len(rows), "neighborhoods": len(markets)}


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Austin"
    state = sys.argv[2] if len(sys.argv) > 2 else "TX"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    result = import_listings(city, state, limit=limit)
    print(f"Imported {result['listings']} listings, {result['neighborhoods']} zip markets")
