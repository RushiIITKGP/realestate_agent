import json
from typing import Annotated

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from app.services.property_search import (
    NeighborhoodService,
    PropertySearchService,
    collected_properties_ctx,
    db_session_ctx,
)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    preferences: dict


def _get_db():
    db = db_session_ctx.get()
    if db is None:
        raise RuntimeError("Database session is not available in agent context.")
    return db


def _track_properties(properties) -> None:
    if not properties:
        return
    current = list(collected_properties_ctx.get())
    seen = {item.id for item in current}
    for prop in properties:
        if prop.id not in seen:
            current.append(prop)
            seen.add(prop.id)
    collected_properties_ctx.set(current)


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
    limit: int = 10,
) -> str:
    """Search available home listings by location, price, beds/baths, property type, neighborhood, walkability, schools, or keywords."""
    from app.schemas.property import PropertySearchParams

    db = _get_db()
    service = PropertySearchService(db)
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
        limit=limit,
    )
    results = service.search(params)
    _track_properties(results)
    return json.dumps(
        {
            "count": len(results),
            "listings": [service.summarize(item) for item in results],
        }
    )


@tool
def get_property_details(property_id: str) -> str:
    """Get full details for a specific listing by property ID."""
    db = _get_db()
    service = PropertySearchService(db)
    property_obj = service.get_by_id(property_id)
    if property_obj is None:
        return json.dumps({"error": "Property not found"})
    _track_properties([property_obj])
    return json.dumps({"property": service.detail(property_obj)})


@tool
def get_neighborhood_info(neighborhood: str, city: str | None = None) -> str:
    """Get neighborhood guide information including walkability, schools, amenities, and median prices."""
    db = _get_db()
    service = NeighborhoodService(db)
    return service.search_json(neighborhood, city)


@tool
def compare_properties(property_ids: list[str]) -> str:
    """Compare two to four listings side by side by property IDs."""
    db = _get_db()
    result = PropertySearchService.compare(property_ids, db)
    _track_properties(PropertySearchService(db).get_many_by_ids(property_ids))
    return json.dumps(result)


AGENT_TOOLS = [
    search_properties,
    get_property_details,
    get_neighborhood_info,
    compare_properties,
]


def build_agent_graph(model):
    tool_node = ToolNode(AGENT_TOOLS)

    def agent_node(state: AgentState):
        response = model.bind_tools(AGENT_TOOLS).invoke(state["messages"])
        return {"messages": [response]}

    def update_preferences(state: AgentState):
        prefs = dict(state.get("preferences") or {})
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for call in last_message.tool_calls:
                if call["name"] == "search_properties":
                    for key, value in call["args"].items():
                        if value is not None:
                            prefs[key] = value
        return {"preferences": prefs}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("update_preferences", update_preferences)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "update_preferences", END: END})
    graph.add_edge("update_preferences", "tools")
    graph.add_edge("tools", "agent")

    return graph
