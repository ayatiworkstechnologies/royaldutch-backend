"""Remove price and duration from the service catalogue.

Revision ID: 20261015_0010
Revises: 20261009_0009
"""

from alembic import op


revision = "20261015_0010"
down_revision = "20261009_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("services", "price")
    op.drop_column("services", "duration_minutes")


def downgrade() -> None:
    # Restoring these fields does not recover historic service values.
    import sqlalchemy as sa

    op.add_column("services", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("services", sa.Column("price", sa.Numeric(10, 2), nullable=True))
