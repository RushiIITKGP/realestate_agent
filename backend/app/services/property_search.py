import json
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import tool
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models import Neighborhood, Property
from app.models.property import PropertyType
from app.schemas.property import PropertySearchParams


db_session_ctx: ContextVar[Session | None] = ContextVar("db_session", default=None)
collected_properties_ctx: ContextVar[list[Property]] = ContextVar("collected_properties", default=[])


class PropertySearchService:
    def __init__(self, db: Session):
        self.db = db

    def search(self, params: PropertySearchParams) -> list[Property]:
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

        query = query.order_by(Property.price.asc()).limit(params.limit)
        return list(self.db.scalars(query).all())

    def get_by_id(self, property_id: str) -> Property | None:
        return self.db.get(Property, property_id)

    def get_many_by_ids(self, property_ids: list[str]) -> list[Property]:
        if not property_ids:
            return []
        query = select(Property).where(Property.id.in_(property_ids)).order_by(Property.price.asc())
        return list(self.db.scalars(query).all())

    @staticmethod
    def summarize(property_obj: Property) -> dict[str, Any]:
        return {
            "id": property_obj.id,
            "address": property_obj.address,
            "city": property_obj.city,
            "state": property_obj.state,
            "price": property_obj.price,
            "beds": property_obj.beds,
            "baths": property_obj.baths,
            "sqft": property_obj.sqft,
            "neighborhood": property_obj.neighborhood,
            "property_type": property_obj.property_type.value,
            "school_rating": property_obj.school_rating,
            "walk_score": property_obj.walk_score,
            "summary": property_obj.description,
        }

    @staticmethod
    def detail(property_obj: Property) -> dict[str, Any]:
        data = PropertySearchService.summarize(property_obj)
        data.update(
            {
                "zip": property_obj.zip,
                "year_built": property_obj.year_built,
                "status": property_obj.status.value,
                "features": property_obj.features,
                "commute": property_obj.commute_downtown,
                "description": property_obj.description,
                "image_url": property_obj.image_url,
            }
        )
        return data

    @staticmethod
    def compare(property_ids: list[str], db: Session) -> dict[str, Any]:
        service = PropertySearchService(db)
        properties = service.get_many_by_ids(property_ids)
        return {
            "compared": [
                {
                    "id": item.id,
                    "address": item.address,
                    "price": item.price,
                    "beds": item.beds,
                    "baths": item.baths,
                    "sqft": item.sqft,
                    "neighborhood": item.neighborhood,
                    "walk_score": item.walk_score,
                    "school_rating": item.school_rating,
                    "highlights": item.features[:4],
                }
                for item in properties
            ]
        }


class NeighborhoodService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, name: str, city: str | None = None) -> Neighborhood | None:
        query = select(Neighborhood).where(func.lower(Neighborhood.name) == name.lower())
        if city:
            query = query.where(func.lower(Neighborhood.city) == city.lower())
        return self.db.scalars(query).first()

    @staticmethod
    def serialize(neighborhood: Neighborhood) -> dict[str, Any]:
        return {
            "id": neighborhood.id,
            "name": neighborhood.name,
            "city": neighborhood.city,
            "state": neighborhood.state,
            "summary": neighborhood.summary,
            "median_price": neighborhood.median_price,
            "walk_score": neighborhood.walk_score,
            "school_rating": neighborhood.school_rating,
            "highlights": neighborhood.highlights,
            "nearby_amenities": neighborhood.nearby_amenities,
        }

    def search_json(self, name: str, city: str | None = None) -> str:
        neighborhood = self.get(name, city)
        if neighborhood is None:
            return json.dumps({"error": "Neighborhood guide not found"})
        return json.dumps({"neighborhood": self.serialize(neighborhood)})
