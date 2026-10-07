"""Allow sub-service prices to contain ranges.

Revision ID: 561ba1dffeaf
Revises: 20260911_0007
Create Date: 2026-10-07 12:06:49.640409
"""
from alembic import op
import sqlalchemy as sa


revision = '561ba1dffeaf'
down_revision = '20260911_0007'
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
        with op.batch_alter_table("sub_services") as batch_op:
            batch_op.alter_column(
                "price",
                existing_type=sa.Numeric(10, 2),
                type_=sa.String(50),
                existing_nullable=True,
            )


def downgrade() -> None:
    connection = op.get_bind()
    # Ranges cannot be represented by NUMERIC. Preserve exact prices and turn
    # ranges into NULL instead of arbitrarily choosing one endpoint.
    if connection.dialect.name == "postgresql":
        op.alter_column(
            "sub_services",
            "price",
            existing_type=sa.String(50),
            type_=sa.Numeric(10, 2),
            existing_nullable=True,
            postgresql_using="CASE WHEN price LIKE '%-%' THEN NULL ELSE price::numeric END",
        )
    else:
        connection.execute(sa.text("UPDATE sub_services SET price = NULL WHERE price LIKE '%-%'"))
        with op.batch_alter_table("sub_services") as batch_op:
            batch_op.alter_column(
                "price",
                existing_type=sa.String(50),
                type_=sa.Numeric(10, 2),
                existing_nullable=True,
            )
