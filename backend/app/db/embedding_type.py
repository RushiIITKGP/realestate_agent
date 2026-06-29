from sqlalchemy.types import JSON, TypeDecorator

EMBEDDING_DIMENSION = 768


class EmbeddingType(TypeDecorator):
    """JSON on SQLite; pgvector Vector(768) on PostgreSQL."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector

            return dialect.type_descriptor(Vector(EMBEDDING_DIMENSION))
        return dialect.type_descriptor(JSON())
