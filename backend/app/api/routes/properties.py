from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.property import PropertyDetail, PropertySearchParams, PropertySummary
from app.services import properties as property_db

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertySummary])
def list_properties(
    city: str | None = None,
    state: str | None = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    min_beds: int | None = Query(default=None, ge=0),
    min_baths: float | None = Query(default=None, ge=0),
    property_type: str | None = None,
    neighborhood: str | None = None,
    min_school_rating: int | None = Query(default=None, ge=1, le=10),
    min_walk_score: int | None = Query(default=None, ge=0, le=100),
    keywords: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[PropertySummary]:
    params = PropertySearchParams(
        city=city,
        state=state,
        min_price=min_price,
        max_price=max_price,
        min_beds=min_beds,
        min_baths=min_baths,
        property_type=property_type,
        neighborhood=neighborhood,
        min_school_rating=min_school_rating,
        min_walk_score=min_walk_score,
        keywords=keywords,
        limit=limit,
    )
    return property_db.search(db, params)


@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(property_id: str, db: Session = Depends(get_db)) -> PropertyDetail:
    prop = property_db.get_by_id(db, property_id)
    if prop is None:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop
