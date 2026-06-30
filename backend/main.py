import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
from sqlalchemy import JSON, Float, Integer, String, Text, create_engine, func, or_, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from data import NEIGHBORHOODS, PROPERTIES

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite-preview")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/realestate.db")
USE_MOCK_DATA = os.getenv("USE_MOCK_DATA", "true").lower() == "true"

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


def seed_db() -> None:
    with Session(engine) as db:
        if db.scalar(select(func.count()).select_from(Property)):
            return
        if not USE_MOCK_DATA:
            return
        for row in PROPERTIES:
            db.add(Property(**row))
        for row in NEIGHBORHOODS:
            db.add(Neighborhood(**row))
        db.commit()


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


seed_db()

app = FastAPI(title="HomeGuide AI")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/listings/import")
def import_real_listings(city: str = "Austin", state: str = "TX", limit: int = 20):
    """Fetch real for-sale listings from RentCast into the database."""
    from fetch_data import import_listings

    try:
        result = import_listings(city=city, state=state, limit=limit, replace=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, f"Data import failed: {exc}") from exc

    return {
        "message": f"Imported {result['listings']} listings",
        "city": city,
        "state": state,
        "neighborhoods": result["neighborhoods"],
    }


@app.post("/chat/stream")
def chat_stream(body: ChatRequest):
    if not GOOGLE_API_KEY:
        raise HTTPException(503, "Set GOOGLE_API_KEY in backend/.env")

    from agent import stream_chat

    def events():
        with Session(engine) as db:
            try:
                for event in stream_chat(db, body.session_id, body.message):
                    yield f"data: {json.dumps(event)}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
