"""add contacts table

Revision ID: 20260619_0004
Revises: 20260619_0003
Create Date: 2026-06-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260619_0004"
down_revision = "20260619_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "contacts" in set(inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(180), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False, index=True),
        sa.Column("email", sa.String(180), nullable=True, index=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="walk_in"),
        sa.Column("status", sa.String(30), nullable=False, server_default="new", index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("contacts")
