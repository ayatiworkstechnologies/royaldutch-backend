"""describe change

Revision ID: af87ee5e3534
Revises: 20261015_0010
Create Date: 2026-10-15 17:04:40.851280
"""
from alembic import op
import sqlalchemy as sa


revision = 'af87ee5e3534'
down_revision = '20261015_0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentionally empty: this revision was already applied in existing
    # environments before it was given a descriptive name.
    pass


def downgrade() -> None:
    pass
