import json
import math
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import BaseModel
from sqlalchemy import JSON, Float, Integer, String, Text, create_engine, delete, func, or_, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite-preview")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/gemini-embedding-001")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/realestate.db")
RENTCAST_API_KEY = os.getenv("RENTCAST_API_KEY")
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Austin")
DEFAULT_STATE = os.getenv("DEFAULT_STATE", "TX")
DEFAULT_IMPORT_LIMIT = int(os.getenv("DEFAULT_IMPORT_LIMIT", "20"))
AUTO_IMPORT = os.getenv("AUTO_IMPORT", "true").lower() == "true"

LISTINGS_URL = "https://api.rentcast.io/v1/listings/sale"
MARKETS_URL = "https://api.rentcast.io/v1/markets"

Path(DATABASE_URL.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    zip: Mapped[str] = mapped_column(String(10))
    price: Mapped[int] = mapped_column(Integer)
    beds: Mapped[int] = mapped_column(Integer)
    baths: Mapped[float] = mapped_column(Float)
    sqft: Mapped[int] = mapped_column(Integer)
    property_type: Mapped[str] = mapped_column(String(20))
    year_built: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    features: Mapped[list] = mapped_column(JSON)
    neighborhood: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20))
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    summary: Mapped[str] = mapped_column(Text)
    median_price: Mapped[int] = mapped_column(Integer)
    highlights: Mapped[list] = mapped_column(JSON)


Base.metadata.create_all(engine)


def _ensure_embedding_column() -> None:
    with engine.connect() as conn:
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(properties)"))}
        if "embedding" not in cols:
            conn.execute(text("ALTER TABLE properties ADD COLUMN embedding JSON"))
            conn.commit()


_ensure_embedding_column()


def property_embed_text(prop: Property | dict) -> str:
    if isinstance(prop, dict):
        features = ", ".join(prop.get("features") or [])
        return (
            f"{prop.get('description', '')} Features: {features}. "
            f"Type: {prop.get('property_type', '')}. "
            f"{prop.get('beds', 0)} bed {prop.get('baths', 0)} bath {prop.get('sqft', 0)} sqft "
            f"in {prop.get('neighborhood', '')}, {prop.get('city', '')}."
        )
    features = ", ".join(prop.features or [])
    return (
        f"{prop.description} Features: {features}. Type: {prop.property_type}. "
        f"{prop.beds} bed {prop.baths} bath {prop.sqft} sqft "
        f"in {prop.neighborhood}, {prop.city}."
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not GOOGLE_API_KEY:
        raise ValueError("Set GOOGLE_API_KEY in backend/.env")
    if not texts:
        return []
    embedder = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=GOOGLE_API_KEY)
    return embedder.embed_documents(texts)


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def index_embeddings(db: Session, property_ids: list[str] | None = None) -> int:
    query = select(Property).where(Property.embedding.is_(None))
    if property_ids:
        query = query.where(Property.id.in_(property_ids))
    props = list(db.scalars(query))
    if not props:
        return 0

    vectors = embed_texts([property_embed_text(p) for p in props])
    for prop, vector in zip(props, vectors):
        prop.embedding = vector
    db.commit()
    return len(props)


def _property_type(raw: str | None) -> str:
    value = (raw or "").lower()
    if "condo" in value:
        return "condo"
    if "town" in value:
        return "townhouse"
    return "house"


def fetch_sale_listings(city: str, state: str, limit: int = 20) -> list[dict]:
    if not RENTCAST_API_KEY:
        raise ValueError("Set RENTCAST_API_KEY in backend/.env (https://app.rentcast.io)")

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


def import_listings(city: str, state: str, limit: int = 20, replace: bool = True) -> dict:
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

    embedded = 0
    if GOOGLE_API_KEY:
        with Session(engine) as db:
            embedded = index_embeddings(db)

    return {"listings": len(rows), "neighborhoods": len(markets), "embedded": embedded}


def ensure_listings() -> None:
    with Session(engine) as db:
        if db.scalar(select(func.count()).select_from(Property)):
            missing = db.scalar(
                select(func.count()).select_from(Property).where(Property.embedding.is_(None))
            )
            if missing:
                index_embeddings(db)
            return
    if not RENTCAST_API_KEY:
        return
    import_listings(DEFAULT_CITY, DEFAULT_STATE, limit=DEFAULT_IMPORT_LIMIT)


def search_listings(
    db: Session,
    city: str | None = None,
    max_price: int | None = None,
    min_beds: int | None = None,
    keywords: str | None = None,
    limit: int = 10,
) -> list[Property]:
    query = select(Property)
    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    if max_price is not None:
        query = query.where(Property.price <= max_price)
    if min_beds is not None:
        query = query.where(Property.beds >= min_beds)
    if keywords:
        for word in keywords.lower().split():
            pattern = f"%{word}%"
            query = query.where(
                or_(
                    func.lower(Property.description).like(pattern),
                    func.lower(Property.neighborhood).like(pattern),
                    func.lower(Property.address).like(pattern),
                )
            )
    return list(db.scalars(query.order_by(Property.price).limit(limit)))


def search_similar_listings(
    db: Session,
    property_id: str,
    limit: int = 5,
    city: str | None = None,
    max_price: int | None = None,
) -> list[Property]:
    ref = get_listing(db, property_id)
    if not ref or not ref.embedding:
        return []

    query = select(Property).where(Property.embedding.isnot(None), Property.id != property_id)
    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    if max_price is not None:
        query = query.where(Property.price <= max_price)

    scored = [(_cosine(ref.embedding, p.embedding), p) for p in db.scalars(query)]
    scored.sort(key=lambda row: row[0], reverse=True)
    return [p for _, p in scored[:limit]]


def search_semantic(
    db: Session,
    query_text: str,
    city: str | None = None,
    max_price: int | None = None,
    limit: int = 10,
) -> list[Property]:
    vector = embed_text(query_text)
    sql = select(Property).where(Property.embedding.isnot(None))
    if city:
        sql = sql.where(func.lower(Property.city) == city.lower())
    if max_price is not None:
        sql = sql.where(Property.price <= max_price)

    scored = [(_cosine(vector, p.embedding), p) for p in db.scalars(sql)]
    scored.sort(key=lambda row: row[0], reverse=True)
    return [p for _, p in scored[:limit]]


def get_listing(db: Session, property_id: str) -> Property | None:
    return db.get(Property, property_id)


def get_neighborhood(db: Session, name: str, city: str | None = None) -> Neighborhood | None:
    query = select(Neighborhood).where(
        or_(
            func.lower(Neighborhood.name) == name.lower(),
            Neighborhood.id == f"zip-{name}",
        )
    )
    if city:
        query = query.where(func.lower(Neighborhood.city) == city.lower())
    return db.scalars(query).first()


def listing_card(prop: Property) -> dict:
    return {
        "id": prop.id,
        "address": prop.address,
        "city": prop.city,
        "state": prop.state,
        "price": prop.price,
        "beds": prop.beds,
        "baths": prop.baths,
        "sqft": prop.sqft,
        "neighborhood": prop.neighborhood,
        "property_type": prop.property_type,
        "description": prop.description,
    }


app = FastAPI(title="HomeGuide AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def load_listings_on_startup():
    if AUTO_IMPORT:
        ensure_listings()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/listings/import")
def import_real_listings(city: str = "Austin", state: str = "TX", limit: int = 20):
    try:
        result = import_listings(city=city, state=state, limit=limit, replace=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"RentCast import failed: {exc}") from exc

    return {
        "message": f"Imported {result['listings']} listings",
        "city": city,
        "state": state,
        "neighborhoods": result["neighborhoods"],
        "embedded": result.get("embedded", 0),
    }


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(503, "Set GOOGLE_API_KEY in backend/.env")
    if not RENTCAST_API_KEY:
        raise HTTPException(503, "Set RENTCAST_API_KEY in backend/.env")

    from agent import stream_chat

    def events():
        with Session(engine) as db:
            try:
                for event in stream_chat(db, body.session_id, body.message):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CITY
    state = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_STATE
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_IMPORT_LIMIT
    result = import_listings(city, state, limit=limit)
    print(f"Imported {result['listings']} listings, {result['neighborhoods']} zip markets")
