from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import chat, health, properties
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.seed.seed import seed_database
from app.services import properties as property_db
from app.services.embeddings import embed_properties

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        with SessionLocal() as db:
            seed_database(db)
            if settings.semantic_search_enabled and property_db.count_missing_embeddings(db) > 0:
                try:
                    count = embed_properties(db)
                    logger.info("Indexed embeddings for %s properties", count)
                except Exception as exc:
                    logger.warning("Embedding index skipped: %s", exc)
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    app.include_router(health.router)
    app.include_router(properties.router)
    app.include_router(chat.router)

    return app


app = create_app()
