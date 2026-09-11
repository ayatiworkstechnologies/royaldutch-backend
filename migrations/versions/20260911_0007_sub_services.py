"""Add sub-services belonging to services."""
from alembic import op
import sqlalchemy as sa

revision = "20260911_0007"
down_revision = "20260910_0006"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    # MySQL/TiDB DDL can survive a failed migration without advancing the
    # Alembic revision, so this migration must be safe to resume.
    if not inspector.has_table("sub_services"):
        op.create_table(
            "sub_services",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id"), nullable=False),
            sa.Column("name", sa.String(180), nullable=False),
            sa.Column("slug", sa.String(220), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("price", sa.Numeric(10, 2), nullable=True),
            sa.Column("currency", sa.String(10), nullable=False),
            sa.Column("image", sa.String(500), nullable=True),
            sa.Column("status", sa.Enum("active", "inactive", name="recordstatus"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("service_id", "slug", name="uq_sub_service_slug"),
        )
        inspector = sa.inspect(connection)
    indexes = {index["name"] for index in inspector.get_indexes("sub_services")}
    if "ix_sub_services_service_id" not in indexes:
        op.create_index("ix_sub_services_service_id", "sub_services", ["service_id"])


def downgrade():
    op.drop_table("sub_services")
