from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings


def get_llm() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        google_api_key=settings.google_api_key,
    )
