"""link user to staff record

Revision ID: 20260619_0003
Revises: 20260614_0002
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260619_0003"
down_revision = "20260614_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns("users")}
    if "staff_id" not in cols:
        op.add_column("users", sa.Column("staff_id", sa.Integer(), sa.ForeignKey("staff.id"), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("users", "staff_id")
