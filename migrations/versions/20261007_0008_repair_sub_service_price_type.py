"""Repair sub-service price storage for exact amounts and ranges.

Revision ID: 20261007_0008
Revises: 561ba1dffeaf
Create Date: 2026-10-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20261007_0008"
down_revision = "561ba1dffeaf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.alter_column(
            "sub_services",
            "price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.String(50),
            existing_nullable=True,
            postgresql_using="price::text",
        )
    else:
        op.alter_column(
            "sub_services",
            "price",
            existing_type=sa.Numeric(10, 2),
            type_=sa.String(50),
            existing_nullable=True,
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE sub_services SET price = NULL WHERE price LIKE '%-%'"))
    if connection.dialect.name == "postgresql":
        op.alter_column(
            "sub_services",
            "price",
            existing_type=sa.String(50),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            postgresql_using="price::numeric",
        )
    else:
        op.alter_column(
            "sub_services",
            "price",
            existing_type=sa.String(50),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
        )
