#!/usr/bin/env python3
"""Re-index property embeddings (run after seeding or description updates)."""

from app.db.session import SessionLocal, init_db
from app.services.embeddings import embed_properties
from app.services import properties as property_db


def main() -> None:
    init_db()
    with SessionLocal() as db:
        missing = property_db.count_missing_embeddings(db)
        total = embed_properties(db)
        print(f"Indexed embeddings for {total} properties ({missing} were missing).")


if __name__ == "__main__":
    main()
