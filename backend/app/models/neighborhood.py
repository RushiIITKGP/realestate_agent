from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.base import Base


class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    median_price: Mapped[int] = mapped_column(Integer, nullable=False)
    walk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    school_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    highlights: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    nearby_amenities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
