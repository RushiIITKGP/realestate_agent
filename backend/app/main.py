from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import chat, health, properties
from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.seed.seed import seed_database


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        with SessionLocal() as db:
            seed_database(db)
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

    app.include_router(health.router)
    app.include_router(properties.router)
    app.include_router(chat.router)

    return app


app = create_app()
