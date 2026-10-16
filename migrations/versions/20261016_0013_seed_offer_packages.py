"""Seed the original homepage offers against Packages-list.

Revision ID: 20261016_0013
Revises: 20261016_0012
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20261016_0013"
down_revision = "20261016_0012"
branch_labels = None
depends_on = None


OFFERS = (
    ("Executive Health Checkup", "A little peace of mind starts with a complete picture of your health.", "/images/executive-health-checkup.png", 1999, 999),
    ("Diabetes Monitoring", "Stay a step ahead with care focused on your everyday wellbeing.", "/images/diabetes-monitoring.png", 999, 699),
    ("Annual GP Membership", "Your health, supported. A familiar face for every stage of the year.", "/images/annual-gp-membership.png", 2000, 1500),
    ("Family Dental Package", "A healthier smile for every generation. Care for the whole family.", "/images/family-dental-package.png", 1800, 1200),
)


def upgrade() -> None:
    connection = op.get_bind()
    service_id = connection.execute(
        sa.text("SELECT id FROM services WHERE slug = :slug LIMIT 1"),
        {"slug": "packages-list"},
    ).scalar()
    if service_id is None:
        return
    for title, description, image_url, original_price, offer_price in OFFERS:
        exists = connection.execute(
            sa.text("SELECT id FROM offer_packages WHERE title = :title LIMIT 1"),
            {"title": title},
        ).scalar()
        if exists is None:
            connection.execute(
                sa.text(
                    "INSERT INTO offer_packages "
                    "(service_id, title, description, image_url, original_price, offer_price, currency, status, created_at, updated_at) "
                    "VALUES (:service_id, :title, :description, :image_url, :original_price, :offer_price, 'AED', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                ),
                {
                    "service_id": service_id,
                    "title": title,
                    "description": description,
                    "image_url": image_url,
                    "original_price": original_price,
                    "offer_price": offer_price,
                },
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM offer_packages WHERE title IN :titles").bindparams(
            sa.bindparam("titles", expanding=True)
        ),
        {"titles": [item[0] for item in OFFERS]},
    )
