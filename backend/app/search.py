import math
from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Neighborhood, Property
from app.schemas import PropertySearchParams


def _apply_filters(query, params: PropertySearchParams):
    if params.city:
        query = query.where(func.lower(Property.city) == params.city.lower())
    if params.state:
        query = query.where(func.lower(Property.state) == params.state.lower())
    if params.min_price is not None:
        query = query.where(Property.price >= params.min_price)
    if params.max_price is not None:
        query = query.where(Property.price <= params.max_price)
    if params.min_beds is not None:
        query = query.where(Property.beds >= params.min_beds)
    if params.min_baths is not None:
        query = query.where(Property.baths >= params.min_baths)
    if params.property_type:
        query = query.where(Property.property_type == params.property_type)
    if params.neighborhood:
        query = query.where(func.lower(Property.neighborhood) == params.neighborhood.lower())
    if params.min_school_rating is not None:
        query = query.where(Property.school_rating >= params.min_school_rating)
    if params.min_walk_score is not None:
        query = query.where(Property.walk_score >= params.min_walk_score)

    keywords = params.semantic_query or params.keywords
    if keywords and not params.semantic_query:
        for word in keywords.lower().split():
            pattern = f"%{word}%"
            query = query.where(
                or_(
                    func.lower(Property.description).like(pattern),
                    func.lower(Property.neighborhood).like(pattern),
                    func.lower(Property.address).like(pattern),
                    func.lower(cast(Property.features, String)).like(pattern),
                )
            )
    return query


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _rank_by_embedding(candidates: list[Property], query_vector: list[float], limit: int) -> list[Property]:
    scored = [
        (_cosine_similarity(query_vector, prop.embedding), prop)
        for prop in candidates
        if prop.embedding is not None
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [prop for _, prop in scored[:limit]]


def property_to_text(prop: Property) -> str:
    features = ", ".join(prop.features)
    return (
        f"{prop.address}, {prop.city}, {prop.state}. "
        f"{prop.neighborhood} neighborhood. "
        f"{prop.beds} bed, {prop.baths} bath, ${prop.price:,}. "
        f"{prop.description} Features: {features}."
    )


@lru_cache
def _get_embedder() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


def clear_embeddings(db: Session) -> None:
    for prop in db.scalars(select(Property)).all():
        prop.embedding = None
    db.commit()


def embed_text(text: str) -> list[float] | None:
    try:
        return _get_embedder().embed_query(text)
    except Exception:
        return None


def embed_properties(db: Session, properties: list[Property] | None = None) -> int:
    if properties is None:
        properties = list(db.scalars(select(Property)).all())
    if not properties:
        return 0

    texts = [property_to_text(p) for p in properties]
    try:
        vectors = _get_embedder().embed_documents(texts)
    except Exception:
        return 0

    for prop, vector in zip(properties, vectors):
        prop.embedding = vector
    db.commit()
    return len(properties)


def count_missing_embeddings(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Property).where(Property.embedding.is_(None))) or 0


def search(db: Session, params: PropertySearchParams) -> list[Property]:
    query = _apply_filters(select(Property), params)

    if params.semantic_query and get_settings().llm_configured:
        query_vector = embed_text(params.semantic_query)
        if query_vector:
            candidates = list(db.scalars(query).all())
            ranked = _rank_by_embedding(candidates, query_vector, params.limit)
            if ranked:
                return ranked

        fallback = PropertySearchParams(
            **{**params.model_dump(), "keywords": params.semantic_query, "semantic_query": None}
        )
        return search(db, fallback)

    return list(db.scalars(query.order_by(Property.price.asc()).limit(params.limit)).all())


def find_similar(db: Session, property_id: str, limit: int = 5, max_price: int | None = None) -> list[Property]:
    source = get_by_id(db, property_id)
    if source is None or source.embedding is None:
        return []

    query = select(Property).where(Property.id != property_id)
    if max_price is not None:
        query = query.where(Property.price <= max_price)
    candidates = list(db.scalars(query).all())
    return _rank_by_embedding(candidates, source.embedding, limit)


def get_by_id(db: Session, property_id: str) -> Property | None:
    return db.get(Property, property_id)


def get_by_ids(db: Session, property_ids: list[str]) -> list[Property]:
    if not property_ids:
        return []
    return list(
        db.scalars(select(Property).where(Property.id.in_(property_ids)).order_by(Property.price.asc())).all()
    )


def get_neighborhood(db: Session, name: str, city: str | None = None) -> Neighborhood | None:
    query = select(Neighborhood).where(func.lower(Neighborhood.name) == name.lower())
    if city:
        query = query.where(func.lower(Neighborhood.city) == city.lower())
    return db.scalars(query).first()


def to_summary(prop: Property) -> dict:
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
        "school_rating": prop.school_rating,
        "walk_score": prop.walk_score,
        "description": prop.description,
        "image_url": prop.image_url,
    }


def to_detail(prop: Property) -> dict:
    return {
        **to_summary(prop),
        "zip": prop.zip,
        "year_built": prop.year_built,
        "status": prop.status,
        "features": prop.features,
        "commute": prop.commute_downtown,
    }


def neighborhood_to_dict(hood: Neighborhood) -> dict:
    return {
        "id": hood.id,
        "name": hood.name,
        "city": hood.city,
        "state": hood.state,
        "summary": hood.summary,
        "median_price": hood.median_price,
        "walk_score": hood.walk_score,
        "school_rating": hood.school_rating,
        "highlights": hood.highlights,
        "nearby_amenities": hood.nearby_amenities,
    }
