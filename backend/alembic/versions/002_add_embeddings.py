"""add property embeddings

Revision ID: 002
Revises: 001
Create Date: 2025-06-29
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE properties ADD COLUMN IF NOT EXISTS embedding vector(768)")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_properties_embedding "
            "ON properties USING hnsw (embedding vector_cosine_ops)"
        )
    else:
        op.add_column("properties", sa.Column("embedding", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_properties_embedding")
        op.drop_column("properties", "embedding")
    else:
        op.drop_column("properties", "embedding")
