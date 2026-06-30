import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agent import ChatError, run_chat, stream_chat
from app.config import get_settings
from app.db import SessionLocal, get_db, init_db
from app.schemas import ChatRequest, ChatResponse
from app import search as listing_search
from app.seed import seed_database

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        with SessionLocal() as db:
            seed_database(db)
            if settings.llm_configured and listing_search.count_missing_embeddings(db) > 0:
                try:
                    count = listing_search.embed_properties(db)
                    logger.info("Indexed embeddings for %s properties", count)
                except Exception as exc:
                    logger.warning("Embedding index skipped: %s", exc)
        yield

    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
        try:
            return run_chat(db, request.session_id, request.message)
        except ChatError as exc:
            raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    @app.post("/chat/stream")
    def chat_stream(request: ChatRequest):
        if not settings.llm_configured:
            raise HTTPException(
                status_code=503,
                detail="GOOGLE_API_KEY is not configured. Copy backend/.env.example to backend/.env.",
            )

        def events():
            with SessionLocal() as db:
                try:
                    for event in stream_chat(db, request.session_id, request.message):
                        yield f"data: {json.dumps(event)}\n\n"
                except ChatError as exc:
                    yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return app


app = create_app()
