"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-06-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("zip", sa.String(length=10), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("beds", sa.Integer(), nullable=False),
        sa.Column("baths", sa.Float(), nullable=False),
        sa.Column("sqft", sa.Integer(), nullable=False),
        sa.Column("property_type", sa.Enum("HOUSE", "CONDO", "TOWNHOUSE", name="propertytype"), nullable=False),
        sa.Column("year_built", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("neighborhood", sa.String(length=100), nullable=False),
        sa.Column("school_rating", sa.Integer(), nullable=False),
        sa.Column("walk_score", sa.Integer(), nullable=False),
        sa.Column("commute_downtown", sa.String(length=100), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.Enum("FOR_SALE", "PENDING", name="propertystatus"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_properties_city", "properties", ["city"], unique=False)
    op.create_index("ix_properties_neighborhood", "properties", ["neighborhood"], unique=False)
    op.create_index("ix_properties_price", "properties", ["price"], unique=False)
    op.create_index("ix_properties_state", "properties", ["state"], unique=False)

    op.create_table(
        "neighborhoods",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=2), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("median_price", sa.Integer(), nullable=False),
        sa.Column("walk_score", sa.Integer(), nullable=False),
        sa.Column("school_rating", sa.Integer(), nullable=False),
        sa.Column("highlights", sa.JSON(), nullable=False),
        sa.Column("nearby_amenities", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_neighborhoods_city", "neighborhoods", ["city"], unique=False)
    op.create_index("ix_neighborhoods_name", "neighborhoods", ["name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_neighborhoods_name", table_name="neighborhoods")
    op.drop_index("ix_neighborhoods_city", table_name="neighborhoods")
    op.drop_table("neighborhoods")
    op.drop_index("ix_properties_state", table_name="properties")
    op.drop_index("ix_properties_price", table_name="properties")
    op.drop_index("ix_properties_neighborhood", table_name="properties")
    op.drop_index("ix_properties_city", table_name="properties")
    op.drop_table("properties")
