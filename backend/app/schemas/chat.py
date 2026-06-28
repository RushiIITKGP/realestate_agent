from pydantic import BaseModel, Field

from app.schemas.property import PropertySummary


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128, examples=["user-123"])
    message: str = Field(min_length=1, max_length=4000, examples=["3 bed homes in Austin under 800k"])


class UserPreferences(BaseModel):
    city: str | None = None
    state: str | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_beds: int | None = None
    min_baths: float | None = None
    property_type: str | None = None
    neighborhood: str | None = None
    keywords: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    properties: list[PropertySummary] = Field(default_factory=list)
    preferences: UserPreferences | None = None
