from pydantic import BaseModel, Field


class PropertySummary(BaseModel):
    id: str
    address: str
    city: str
    state: str
    price: int
    beds: int
    baths: float
    sqft: int
    neighborhood: str
    property_type: str
    school_rating: int
    walk_score: int
    description: str
    image_url: str | None = None

    model_config = {"from_attributes": True}


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
    semantic_query: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    properties: list[PropertySummary] = Field(default_factory=list)
