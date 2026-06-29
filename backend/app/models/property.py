import enum

from sqlalchemy import Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base
from app.db.embedding_type import EmbeddingType


class PropertyType(str, enum.Enum):
    HOUSE = "house"
    CONDO = "condo"
    TOWNHOUSE = "townhouse"


class PropertyStatus(str, enum.Enum):
    FOR_SALE = "for_sale"
    PENDING = "pending"


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    zip: Mapped[str] = mapped_column(String(10), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    beds: Mapped[int] = mapped_column(Integer, nullable=False)
    baths: Mapped[float] = mapped_column(Float, nullable=False)
    sqft: Mapped[int] = mapped_column(Integer, nullable=False)
    property_type: Mapped[PropertyType] = mapped_column(Enum(PropertyType), nullable=False)
    year_built: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    neighborhood: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    school_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    walk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    commute_downtown: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[PropertyStatus] = mapped_column(
        Enum(PropertyStatus), nullable=False, default=PropertyStatus.FOR_SALE
    )
    embedding: Mapped[list[float] | None] = mapped_column(EmbeddingType, nullable=True)
