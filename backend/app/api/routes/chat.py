from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService, ChatServiceError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    service = ChatService(db)
    try:
        return service.chat(session_id=request.session_id, message=request.message)
    except ChatServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
