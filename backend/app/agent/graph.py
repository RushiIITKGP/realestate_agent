from functools import lru_cache
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from app.agent.tools import build_agent_graph
from app.config import get_settings


def _checkpoint_path() -> str:
    url = get_settings().checkpoint_db_url
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "", 1)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return path
    return url


@lru_cache
def get_checkpointer() -> SqliteSaver:
    return SqliteSaver.from_conn_string(_checkpoint_path())


@lru_cache
def get_compiled_agent():
    from langchain_openai import ChatOpenAI

    settings = get_settings()
    model = ChatOpenAI(
        model=settings.openai_chat_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
    )
    graph = build_agent_graph(model)
    return graph.compile(checkpointer=get_checkpointer())
