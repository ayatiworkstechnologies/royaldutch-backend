"""Add the patient archive flag without rewriting applied migrations.

Revision ID: 20261016_0011
Revises: af87ee5e3534
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20261016_0011"
down_revision = "af87ee5e3534"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.add_column(sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_index("ix_patients_is_active", ["is_active"])


def downgrade() -> None:
    with op.batch_alter_table("patients") as batch:
        batch.drop_index("ix_patients_is_active")
        batch.drop_column("is_active")
