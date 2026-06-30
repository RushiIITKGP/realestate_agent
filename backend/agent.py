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

from main import get_listing, get_neighborhood, listing_card, search_listings

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite-preview")
CHECKPOINT_DB = os.getenv("CHECKPOINT_DB_URL", "sqlite:///./data/checkpoints.db")

PROMPT = """You are HomeGuide AI, a conversational real estate assistant.
Use tools to search listings. Never invent prices or addresses.
Ask clarifying questions if city or budget is missing.
Keep answers short."""


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
        """Search home listings by city, price, beds, or keywords."""
        _emit_status(_status("search_properties", {"city": city}))
        results = search_listings(db, city=city, max_price=max_price, min_beds=min_beds, keywords=keywords, limit=limit)
        found.extend(results)
        return json.dumps({"count": len(results), "listings": [listing_card(p) for p in results]})

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
        """Get neighborhood guide."""
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
                "walk_score": hood.walk_score,
                "school_rating": hood.school_rating,
            }
        )

    return [search_properties, get_property_details, get_neighborhood_info]


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
