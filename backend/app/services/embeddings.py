from functools import lru_cache

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import get_settings
from app.models import Property


def property_to_text(prop: Property) -> str:
    features = ", ".join(prop.features)
    return (
        f"{prop.address}, {prop.city}, {prop.state}. "
        f"{prop.neighborhood} neighborhood. "
        f"{prop.beds} bed, {prop.baths} bath, ${prop.price:,}. "
        f"{prop.description} Features: {features}."
    )


@lru_cache
def get_embedder() -> GoogleGenerativeAIEmbeddings:
    settings = get_settings()
    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        google_api_key=settings.google_api_key,
    )


def embed_text(text: str) -> list[float]:
    return get_embedder().embed_query(text)


def embed_properties(db, properties: list[Property] | None = None) -> int:
    """Compute and store embeddings. Returns count updated."""
    from sqlalchemy import select

    if properties is None:
        properties = list(db.scalars(select(Property)).all())

    if not properties:
        return 0

    texts = [property_to_text(p) for p in properties]
    vectors = get_embedder().embed_documents(texts)

    for prop, vector in zip(properties, vectors):
        prop.embedding = vector

    db.commit()
    return len(properties)
