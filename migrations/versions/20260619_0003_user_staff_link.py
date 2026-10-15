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
        # batch_alter_table recreates the table on SQLite, where ALTER TABLE
        # cannot add a foreign-key constraint, while remaining valid on MySQL.
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("staff_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_users_staff_id_staff", "staff", ["staff_id"], ["id"])
            batch.create_index("ix_users_staff_id", ["staff_id"])


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_staff_id")
        batch.drop_constraint("fk_users_staff_id_staff", type_="foreignkey")
        batch.drop_column("staff_id")
