from pydantic import BaseModel, Field

from app.schemas.property import PropertySummary


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    properties: list[PropertySummary] = Field(default_factory=list)
