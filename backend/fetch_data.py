"""Fetch real for-sale listings from RentCast and load them into SQLite."""

import os
import sys

import httpx
from dotenv import load_dotenv
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

load_dotenv()

RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")
RENTCAST_URL = "https://api.rentcast.io/v1/listings/sale"


def _property_type(raw: str | None) -> str:
    value = (raw or "").lower()
    if "condo" in value:
        return "condo"
    if "town" in value:
        return "townhouse"
    return "house"


def rentcast_to_row(item: dict) -> dict:
    beds = int(item.get("bedrooms") or 0)
    baths = float(item.get("bathrooms") or 0)
    sqft = int(item.get("squareFootage") or 0)
    price = int(item.get("price") or 0)
    city = item.get("city") or ""
    state = item.get("state") or ""
    county = item.get("county") or item.get("zipCode") or "Area"
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
        "zip": item.get("zipCode") or "",
        "price": price,
        "beds": beds,
        "baths": baths,
        "sqft": sqft,
        "property_type": _property_type(prop_type),
        "year_built": int(item.get("yearBuilt") or 0),
        "description": description,
        "features": features,
        "neighborhood": county,
        "school_rating": 7,
        "walk_score": 70,
        "commute_downtown": "N/A",
        "image_url": None,
        "status": "for_sale",
    }


def fetch_sale_listings(city: str, state: str, limit: int = 20) -> list[dict]:
    if not RENTCAST_API_KEY:
        raise ValueError("Set RENTCAST_API_KEY in backend/.env (free key at https://rentcast.io)")

    response = httpx.get(
        RENTCAST_URL,
        params={"city": city, "state": state, "status": "Active", "limit": limit},
        headers={"X-Api-Key": RENTCAST_API_KEY},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"Unexpected RentCast response: {data}")
    return data


def import_listings(city: str, state: str, limit: int = 20, replace: bool = True) -> int:
    from main import Property, engine

    listings = fetch_sale_listings(city, state, limit)
    rows = [rentcast_to_row(item) for item in listings]

    with Session(engine) as db:
        if replace:
            db.execute(delete(Property))
        for row in rows:
            db.merge(Property(**row))
        db.commit()

    return len(rows)


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Austin"
    state = sys.argv[2] if len(sys.argv) > 2 else "TX"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    count = import_listings(city, state, limit=limit)
    print(f"Imported {count} real listings for {city}, {state}")
