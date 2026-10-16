"""Add independently managed homepage offer packages and booking linkage.

Revision ID: 20261016_0012
Revises: 20261016_0011
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20261016_0012"
down_revision = "20261016_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    # Development startup may create newly imported model tables before
    # Alembic runs. Detect that partial state and finish only missing work.
    if "offer_packages" not in inspector.get_table_names():
        op.create_table(
            "offer_packages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("service_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("image_url", sa.String(length=500), nullable=False),
            sa.Column("original_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("offer_price", sa.Numeric(10, 2), nullable=False),
            sa.Column("currency", sa.String(length=10), nullable=False, server_default="AED"),
            sa.Column("status", sa.Enum("active", "inactive", name="recordstatus"), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_offer_packages_id", "offer_packages", ["id"])
        op.create_index("ix_offer_packages_service_id", "offer_packages", ["service_id"])

    booking_columns = {column["name"] for column in sa.inspect(connection).get_columns("bookings")}
    if "offer_package_id" not in booking_columns:
        with op.batch_alter_table("bookings") as batch:
            batch.add_column(sa.Column("offer_package_id", sa.Integer(), nullable=True))
            batch.create_foreign_key("fk_bookings_offer_package_id", "offer_packages", ["offer_package_id"], ["id"])
            batch.create_index("ix_bookings_offer_package_id", ["offer_package_id"])


def downgrade() -> None:
    with op.batch_alter_table("bookings") as batch:
        batch.drop_index("ix_bookings_offer_package_id")
        batch.drop_constraint("fk_bookings_offer_package_id", type_="foreignkey")
        batch.drop_column("offer_package_id")
    op.drop_index("ix_offer_packages_service_id", table_name="offer_packages")
    op.drop_index("ix_offer_packages_id", table_name="offer_packages")
    op.drop_table("offer_packages")
