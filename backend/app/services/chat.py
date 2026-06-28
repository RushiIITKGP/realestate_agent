from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.agent.graph import get_compiled_agent
from app.agent.prompts import SYSTEM_PROMPT
from app.config import get_settings
from app.schemas.chat import ChatResponse, UserPreferences
from app.schemas.property import PropertySummary
from app.services.property_search import collected_properties_ctx, db_session_ctx


class ChatServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def chat(self, session_id: str, message: str) -> ChatResponse:
        settings = get_settings()
        if not settings.openai_api_key:
            raise ChatServiceError(
                "OPENAI_API_KEY is not configured. Copy backend/.env.example to backend/.env.",
                status_code=503,
            )

        db_session_ctx.set(self.db)
        collected_properties_ctx.set([])

        agent = get_compiled_agent()
        config = {"configurable": {"thread_id": session_id}}
        snapshot = agent.get_state(config)

        messages = [HumanMessage(content=message)]
        if not snapshot.values.get("messages"):
            messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]

        try:
            result = agent.invoke({"messages": messages}, config=config)
        except Exception as exc:
            raise ChatServiceError(
                f"Agent failed to process the message: {exc}",
                status_code=502,
            ) from exc

        assistant_message = self._extract_assistant_message(result["messages"])
        properties = [
            PropertySummary.model_validate(item, from_attributes=True)
            for item in collected_properties_ctx.get()
        ]
        preferences = UserPreferences.model_validate(result.get("preferences") or {})

        return ChatResponse(
            session_id=session_id,
            message=assistant_message,
            properties=properties,
            preferences=preferences,
        )

    @staticmethod
    def _extract_assistant_message(messages) -> str:
        for message in reversed(messages):
            if isinstance(message, AIMessage) and message.content:
                content = message.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    text_parts = [
                        part.get("text", "")
                        for part in content
                        if isinstance(part, dict) and part.get("type") == "text"
                    ]
                    return "".join(text_parts)
        return "I couldn't generate a response. Please try rephrasing your request."
