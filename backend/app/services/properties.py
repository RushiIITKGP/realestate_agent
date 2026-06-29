import math

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Neighborhood, Property
from app.models.property import PropertyType
from app.schemas.property import PropertySearchParams


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
        query = query.where(Property.property_type == PropertyType(params.property_type))
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


def _search_pgvector(db: Session, query, query_vector: list[float], limit: int) -> list[Property]:
    distance = Property.embedding.cosine_distance(query_vector)
    return list(db.scalars(query.where(Property.embedding.is_not(None)).order_by(distance).limit(limit)).all())


def _search_python_ranked(candidates: list[Property], query_vector: list[float], limit: int) -> list[Property]:
    scored = [
        (_cosine_similarity(query_vector, prop.embedding), prop)
        for prop in candidates
        if prop.embedding is not None
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [prop for _, prop in scored[:limit]]


def search(db: Session, params: PropertySearchParams) -> list[Property]:
    query = _apply_filters(select(Property), params)
    settings = get_settings()

    if params.semantic_query and settings.semantic_search_enabled:
        from app.services.embeddings import embed_text

        query_vector = embed_text(params.semantic_query)

        if settings.is_postgres:
            results = _search_pgvector(db, query, query_vector, params.limit)
            if results:
                return results

        candidates = list(db.scalars(query).all())
        ranked = _search_python_ranked(candidates, query_vector, params.limit)
        if ranked:
            return ranked

        # Fallback: treat semantic_query as keywords if no embeddings yet
        fallback = PropertySearchParams(**{**params.model_dump(), "keywords": params.semantic_query, "semantic_query": None})
        return search(db, fallback)

    return list(db.scalars(query.order_by(Property.price.asc()).limit(params.limit)).all())


def find_similar(db: Session, property_id: str, limit: int = 5, max_price: int | None = None) -> list[Property]:
    source = get_by_id(db, property_id)
    if source is None or source.embedding is None:
        return []

    settings = get_settings()
    query = select(Property).where(Property.id != property_id)
    if max_price is not None:
        query = query.where(Property.price <= max_price)

    if settings.is_postgres:
        distance = Property.embedding.cosine_distance(source.embedding)
        return list(
            db.scalars(
                query.where(Property.embedding.is_not(None)).order_by(distance).limit(limit)
            ).all()
        )

    candidates = list(db.scalars(query).all())
    return _search_python_ranked(candidates, source.embedding, limit)


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


def count_missing_embeddings(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Property).where(Property.embedding.is_(None))) or 0


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
        "property_type": prop.property_type.value,
        "school_rating": prop.school_rating,
        "walk_score": prop.walk_score,
        "summary": prop.description,
    }


def to_detail(prop: Property) -> dict:
    return {
        **to_summary(prop),
        "zip": prop.zip,
        "year_built": prop.year_built,
        "status": prop.status.value,
        "features": prop.features,
        "commute": prop.commute_downtown,
        "description": prop.description,
        "image_url": prop.image_url,
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
