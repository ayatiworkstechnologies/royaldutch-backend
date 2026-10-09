"""Add packages belonging to sub-services.

Revision ID: 20261009_0009
Revises: 20261007_0008
"""
from alembic import op
import sqlalchemy as sa

revision = "20261009_0009"
down_revision = "20261007_0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sub_service_id", sa.Integer(), sa.ForeignKey("sub_services.id"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sessions", sa.Integer(), nullable=True),
        sa.Column("price", sa.String(50), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", name="recordstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("sub_service_id", "slug", name="uq_service_package_slug"),
    )
    op.create_index("ix_service_packages_sub_service_id", "service_packages", ["sub_service_id"])


def downgrade():
    op.drop_table("service_packages")
