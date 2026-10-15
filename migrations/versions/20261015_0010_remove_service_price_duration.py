"""Remove price and duration from the service catalogue.

Revision ID: 20261015_0010
Revises: 20261009_0009
"""

from alembic import op
import sqlalchemy as sa


revision = "20261015_0010"
down_revision = "20261009_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("services") as batch:
        batch.drop_column("price")
        batch.drop_column("duration_minutes")


def downgrade() -> None:
    # Restoring these fields does not recover historic service values.
    with op.batch_alter_table("services") as batch:
        batch.add_column(sa.Column("duration_minutes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("price", sa.Numeric(10, 2), nullable=True))
