from collections.abc import Generator
from pathlib import Path

from sqlalchemy import JSON, Float, Integer, String, Text, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    address: Mapped[str] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(100), index=True)
    state: Mapped[str] = mapped_column(String(2))
    zip: Mapped[str] = mapped_column(String(10))
    price: Mapped[int] = mapped_column(Integer, index=True)
    beds: Mapped[int] = mapped_column(Integer)
    baths: Mapped[float] = mapped_column(Float)
    sqft: Mapped[int] = mapped_column(Integer)
    property_type: Mapped[str] = mapped_column(String(20))
    year_built: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    features: Mapped[list] = mapped_column(JSON)
    neighborhood: Mapped[str] = mapped_column(String(100))
    school_rating: Mapped[int] = mapped_column(Integer)
    walk_score: Mapped[int] = mapped_column(Integer)
    commute_downtown: Mapped[str] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="for_sale")
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)


class Neighborhood(Base):
    __tablename__ = "neighborhoods"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2))
    summary: Mapped[str] = mapped_column(Text)
    median_price: Mapped[int] = mapped_column(Integer)
    walk_score: Mapped[int] = mapped_column(Integer)
    school_rating: Mapped[int] = mapped_column(Integer)
    highlights: Mapped[list] = mapped_column(JSON)
    nearby_amenities: Mapped[list] = mapped_column(JSON)


settings = get_settings()
if settings.database_url.startswith("sqlite:///"):
    Path(settings.database_url.replace("sqlite:///", "", 1)).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_connection, _):
    if settings.database_url.startswith("sqlite"):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_schema()


def _migrate_sqlite_schema() -> None:
    """Add columns missing from older local SQLite DBs (no Alembic)."""
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "properties" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("properties")}
    if "embedding" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE properties ADD COLUMN embedding JSON"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
