import json
import os
import sqlite3
from pathlib import Path

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_stream_writer
from langgraph.prebuilt import create_react_agent
from sqlalchemy.orm import Session

from main import (
    get_listing,
    get_neighborhood,
    listing_card,
    search_listings,
    search_semantic,
    search_similar_listings,
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite-preview")
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB_URL", "sqlite:///./data/checkpoints.db")

PROMPT = """You are HomeGuide AI, a conversational real estate assistant.
Use tools to search listings. Never invent prices or addresses.
Keep answers short.

Pick the search tool based on the user's wording (see each tool's description).
When the user says "the 2nd one" or "that listing", use find_similar_properties with that listing's id."""


def _checkpointer():
    path = CHECKPOINT_DB.replace("sqlite:///", "", 1)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(path, check_same_thread=False))


def _text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "") for block in content if isinstance(block, dict) and block.get("text")
        ).strip()
    return ""


def _status(tool_name: str, args: dict | None = None) -> str:
    args = args or {}
    if tool_name == "search_properties":
        city = args.get("city")
        return f"Searching homes in {city}..." if city else "Searching listings..."
    if tool_name == "search_properties_semantic":
        return "Matching homes by vibe..."
    if tool_name == "find_similar_properties":
        return "Finding similar listings..."
    if tool_name == "get_property_details":
        return "Fetching property details..."
    if tool_name == "get_neighborhood_info":
        return f"Looking up {args.get('neighborhood', 'the area')}..."
    return "Working..."


def _emit_status(message: str) -> None:
    try:
        get_stream_writer()({"type": "status", "content": message})
    except Exception:
        pass


def _make_tools(db: Session, found: list):
    @tool
    def search_properties(
        city: str | None = None,
        max_price: int | None = None,
        min_beds: int | None = None,
        keywords: str | None = None,
        limit: int = 10,
    ) -> str:
        """Filter listings by structured criteria only: city, max price, min beds, or exact keywords.

        Use for plain filters without style or vibe language, e.g. "homes in Austin under 800k"
        or "3 bedroom in Austin". Do NOT use when the user describes style, feel, or aesthetic
        (modern, cozy, minimalist, loft, family-friendly, etc.) — use search_properties_semantic instead."""
        _emit_status(_status("search_properties", {"city": city}))
        results = search_listings(db, city=city, max_price=max_price, min_beds=min_beds, keywords=keywords, limit=limit)
        found.extend(results)
        return json.dumps({"count": len(results), "listings": [listing_card(p) for p in results]})

    @tool
    def search_properties_semantic(
        query: str,
        city: str | None = None,
        max_price: int | None = None,
        limit: int = 10,
    ) -> str:
        """Search by natural language vibe, style, or lifestyle using embeddings.

        Use whenever the user describes how a home feels or looks — including on the first message.
        Also use when vibe language is combined with city or budget in one request.

        Examples:
        - "modern minimalist condo under 600k in Austin" → query="modern minimalist condo", city="Austin", max_price=600000
        - "cozy family home with a yard in Denver"
        - "bright open loft under 500k"

        Put the descriptive phrase in query. Pass city and max_price when the user mentions them."""
        _emit_status(_status("search_properties_semantic"))
        results = search_semantic(db, query, city=city, max_price=max_price, limit=limit)
        found.extend(results)
        return json.dumps({"count": len(results), "listings": [listing_card(p) for p in results]})

    @tool
    def find_similar_properties(
        property_id: str,
        city: str | None = None,
        max_price: int | None = None,
        limit: int = 5,
    ) -> str:
        """Find listings with a similar vibe to a property the user already saw. Use the listing id."""
        _emit_status(_status("find_similar_properties"))
        results = search_similar_listings(
            db, property_id, limit=limit, city=city, max_price=max_price
        )
        found.extend(results)
        ref = get_listing(db, property_id)
        return json.dumps(
            {
                "reference": listing_card(ref) if ref else None,
                "count": len(results),
                "listings": [listing_card(p) for p in results],
            }
        )

    @tool
    def get_property_details(property_id: str) -> str:
        """Get full details for one listing by ID."""
        _emit_status(_status("get_property_details"))
        prop = get_listing(db, property_id)
        if not prop:
            return json.dumps({"error": "not found"})
        found.append(prop)
        data = listing_card(prop)
        data["features"] = prop.features
        data["year_built"] = prop.year_built
        return json.dumps(data)

    @tool
    def get_neighborhood_info(neighborhood: str, city: str | None = None) -> str:
        """Get neighborhood or ZIP code market guide (use ZIP code from a listing, e.g. 78723)."""
        _emit_status(_status("get_neighborhood_info", {"neighborhood": neighborhood}))
        hood = get_neighborhood(db, neighborhood, city)
        if not hood:
            return json.dumps({"error": "not found"})
        return json.dumps(
            {
                "name": hood.name,
                "city": hood.city,
                "summary": hood.summary,
                "median_price": hood.median_price,
                "highlights": hood.highlights,
            }
        )

    return [
        search_properties,
        search_properties_semantic,
        find_similar_properties,
        get_property_details,
        get_neighborhood_info,
    ]


def stream_chat(db: Session, session_id: str, message: str):
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set")

    found = []
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0.7, google_api_key=GOOGLE_API_KEY)
    agent = create_react_agent(llm, _make_tools(db, found), prompt=PROMPT, checkpointer=_checkpointer())
    config = {"configurable": {"thread_id": session_id}}
    payload = {"messages": [HumanMessage(content=message)]}

    yield {"type": "status", "content": "Thinking..."}

    for attempt in range(2):
        try:
            for mode, chunk in agent.stream(
                payload, config=config, stream_mode=["messages", "custom", "updates"]
            ):
                if mode == "custom" and isinstance(chunk, dict) and chunk.get("type") == "status":
                    yield chunk
                elif mode == "updates":
                    for node in chunk.values():
                        if not isinstance(node, dict):
                            continue
                        for msg in node.get("messages", []):
                            if isinstance(msg, AIMessage) and msg.tool_calls:
                                tc = msg.tool_calls[0]
                                yield {"type": "status", "content": _status(tc["name"], tc.get("args") or {})}
                elif mode == "messages":
                    msg, _ = chunk
                    if isinstance(msg, AIMessageChunk):
                        text = _text(msg.content)
                        if text:
                            yield {"type": "text", "content": text}
            break
        except Exception as exc:
            if attempt == 0 and "tool_calls" in str(exc):
                _checkpointer().delete_thread(session_id)
                continue
            raise

    yield {"type": "properties", "properties": [listing_card(p) for p in found]}
    yield {"type": "done"}
