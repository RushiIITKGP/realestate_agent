from pydantic import BaseModel, Field


class PropertySummary(BaseModel):
    id: str
    address: str
    city: str
    state: str
    zip: str
    price: int
    beds: int
    baths: float
    sqft: int
    property_type: str
    neighborhood: str
    school_rating: int
    walk_score: int
    description: str
    features: list[str]
    image_url: str | None = None
    status: str

    model_config = {"from_attributes": True}


class PropertyDetail(PropertySummary):
    year_built: int
    commute_downtown: str


class PropertySearchParams(BaseModel):
    city: str | None = None
    state: str | None = None
    min_price: int | None = Field(default=None, ge=0)
    max_price: int | None = Field(default=None, ge=0)
    min_beds: int | None = Field(default=None, ge=0)
    min_baths: float | None = Field(default=None, ge=0)
    property_type: str | None = None
    neighborhood: str | None = None
    min_school_rating: int | None = Field(default=None, ge=1, le=10)
    min_walk_score: int | None = Field(default=None, ge=0, le=100)
    keywords: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class NeighborhoodResponse(BaseModel):
    id: str
    name: str
    city: str
    state: str
    summary: str
    median_price: int
    walk_score: int
    school_rating: int
    highlights: list[str]
    nearby_amenities: list[str]

    model_config = {"from_attributes": True}
