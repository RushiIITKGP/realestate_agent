from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data_listings import NEIGHBORHOODS, PROPERTIES
from app.db import Neighborhood, Property


def seed_database(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Property)) > 0:
        return

    for row in PROPERTIES:
        db.add(Property(**row))

    for row in NEIGHBORHOODS:
        db.add(Neighborhood(**row))

    db.commit()
