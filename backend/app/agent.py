import json
import sqlite3
from functools import lru_cache
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Property
from app.schemas import ChatResponse, PropertySearchParams, PropertySummary
from app import search as listing_search

SYSTEM_PROMPT = """You are HomeGuide AI, a conversational real estate assistant.

Rules:
- Ask clarifying questions when the request is vague (city, budget, beds).
- Use tools to search listings and fetch details. Never invent listings or prices.
- Use semantic_query in search_properties for natural language (vibe, style, feel).
- Use structured filters (city, max_price, min_beds) for exact constraints.
- Use find_similar_properties when the user wants homes like one they already saw.
- Highlight 2-4 strong matches when presenting results.
- If nothing matches, suggest relaxing one filter at a time.
- You assist buyers; you do not replace a licensed agent.

Keep responses concise."""


class ChatError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@lru_cache
def _get_checkpointer() -> SqliteSaver:
    url = get_settings().checkpoint_db_url
    path = url.replace("sqlite:///", "", 1) if url.startswith("sqlite:///") else url
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    return SqliteSaver(conn)


def _track(found: list[Property], props: list[Property]) -> None:
    seen = {p.id for p in found}
    for prop in props:
        if prop.id not in seen:
            found.append(prop)
            seen.add(prop.id)


def _make_tools(db: Session, found: list[Property]):
    @tool
    def search_properties(
        city: str | None = None,
        state: str | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        min_beds: int | None = None,
        min_baths: float | None = None,
        property_type: str | None = None,
        neighborhood: str | None = None,
        min_school_rating: int | None = None,
        min_walk_score: int | None = None,
        keywords: str | None = None,
        semantic_query: str | None = None,
        limit: int = 10,
    ) -> str:
        """Search listings by filters and/or natural language (semantic_query)."""
        params = PropertySearchParams(
            city=city,
            state=state,
            min_price=min_price,
            max_price=max_price,
            min_beds=min_beds,
            min_baths=min_baths,
            property_type=property_type,
            neighborhood=neighborhood,
            min_school_rating=min_school_rating,
            min_walk_score=min_walk_score,
            keywords=keywords,
            semantic_query=semantic_query,
            limit=limit,
        )
        results = listing_search.search(db, params)
        _track(found, results)
        return json.dumps(
            {"count": len(results), "listings": [listing_search.to_summary(p) for p in results]}
        )

    @tool
    def get_property_details(property_id: str) -> str:
        """Get full details for one listing by property ID."""
        prop = listing_search.get_by_id(db, property_id)
        if prop is None:
            return json.dumps({"error": "Property not found"})
        _track(found, [prop])
        return json.dumps({"property": listing_search.to_detail(prop)})

    @tool
    def get_neighborhood_info(neighborhood: str, city: str | None = None) -> str:
        """Get neighborhood guide: schools, walkability, amenities, median price."""
        hood = listing_search.get_neighborhood(db, neighborhood, city)
        if hood is None:
            return json.dumps({"error": "Neighborhood guide not found"})
        return json.dumps({"neighborhood": listing_search.neighborhood_to_dict(hood)})

    @tool
    def compare_properties(property_ids: list[str]) -> str:
        """Compare 2-4 listings side by side by property ID."""
        props = listing_search.get_by_ids(db, property_ids)
        _track(found, props)
        return json.dumps({"compared": [listing_search.to_summary(p) for p in props]})

    @tool
    def find_similar_properties(
        property_id: str,
        limit: int = 5,
        max_price: int | None = None,
    ) -> str:
        """Find listings similar to a given property ID."""
        results = listing_search.find_similar(db, property_id, limit=limit, max_price=max_price)
        _track(found, results)
        return json.dumps(
            {"count": len(results), "listings": [listing_search.to_summary(p) for p in results]}
        )

    return [
        search_properties,
        get_property_details,
        get_neighborhood_info,
        compare_properties,
        find_similar_properties,
    ]


def _message_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)
        return "\n".join(parts).strip()
    return ""


def _last_ai_text(messages) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = _message_text(message.content)
            if text:
                return text
    return "I couldn't generate a response. Please try again."


def run_chat(db: Session, session_id: str, message: str) -> ChatResponse:
    settings = get_settings()
    if not settings.llm_configured:
        raise ChatError("GOOGLE_API_KEY is not configured. Copy backend/.env.example to backend/.env.", 503)

    found: list[Property] = []
    llm = ChatGoogleGenerativeAI(
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        google_api_key=settings.google_api_key,
    )
    agent = create_react_agent(llm, _make_tools(db, found), prompt=SYSTEM_PROMPT, checkpointer=_get_checkpointer())

    config = {"configurable": {"thread_id": session_id}}
    try:
        result = agent.invoke({"messages": [HumanMessage(content=message)]}, config=config)
    except Exception as exc:
        raise ChatError(f"Agent failed: {exc}", 502) from exc

    return ChatResponse(
        session_id=session_id,
        message=_last_ai_text(result["messages"]),
        properties=[PropertySummary.model_validate(p, from_attributes=True) for p in found],
    )
