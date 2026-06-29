from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent.agent import ChatError, run_chat
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    try:
        return run_chat(db, request.session_id, request.message)
    except ChatError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
