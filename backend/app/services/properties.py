from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models import Neighborhood, Property
from app.models.property import PropertyType
from app.schemas.property import PropertySearchParams


def search(db: Session, params: PropertySearchParams) -> list[Property]:
    query = select(Property)

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

    if params.keywords:
        for word in params.keywords.lower().split():
            pattern = f"%{word}%"
            query = query.where(
                or_(
                    func.lower(Property.description).like(pattern),
                    func.lower(Property.neighborhood).like(pattern),
                    func.lower(Property.address).like(pattern),
                    func.lower(cast(Property.features, String)).like(pattern),
                )
            )

    return list(db.scalars(query.order_by(Property.price.asc()).limit(params.limit)).all())


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
