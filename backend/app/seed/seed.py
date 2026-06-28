"""Seed the database with mock listings and neighborhoods."""

from sqlalchemy.orm import Session

from app.models import Neighborhood, Property
from app.models.property import PropertyStatus, PropertyType
from app.seed.data import NEIGHBORHOODS, PROPERTIES


def seed_database(db: Session) -> None:
    if db.query(Property).count() > 0:
        return

    for row in PROPERTIES:
        db.add(
            Property(
                id=row["id"],
                address=row["address"],
                city=row["city"],
                state=row["state"],
                zip=row["zip"],
                price=row["price"],
                beds=row["beds"],
                baths=row["baths"],
                sqft=row["sqft"],
                property_type=PropertyType(row["property_type"]),
                year_built=row["year_built"],
                description=row["description"],
                features=row["features"],
                neighborhood=row["neighborhood"],
                school_rating=row["school_rating"],
                walk_score=row["walk_score"],
                commute_downtown=row["commute_downtown"],
                image_url=row.get("image_url"),
                status=PropertyStatus(row["status"]),
            )
        )

    for row in NEIGHBORHOODS:
        db.add(Neighborhood(**row))

    db.commit()


if __name__ == "__main__":
    from app.db.session import SessionLocal, init_db

    init_db()
    with SessionLocal() as session:
        seed_database(session)
        print(f"Seeded {len(PROPERTIES)} properties and {len(NEIGHBORHOODS)} neighborhoods.")
