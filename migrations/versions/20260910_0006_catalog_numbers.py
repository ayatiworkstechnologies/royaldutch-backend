"""Persist sequential category and service display IDs."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0006"
down_revision = "89e04b0aba1f"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("catalog_sequences",
        sa.Column("name", sa.String(30), primary_key=True),
        sa.Column("value", sa.Integer(), nullable=False))
    connection = op.get_bind()
    counters = sa.table("catalog_sequences", sa.column("name", sa.String()), sa.column("value", sa.Integer()))
    for name in ("categories", "services"):
        op.add_column(name, sa.Column("display_id", sa.Integer(), nullable=True))
        table = sa.table(name, sa.column("id", sa.Integer()), sa.column("display_id", sa.Integer()))
        ids = connection.execute(sa.select(table.c.id).order_by(table.c.id)).scalars().all()
        for number, record_id in enumerate(ids, 1):
            connection.execute(table.update().where(table.c.id == record_id).values(display_id=number))
        connection.execute(counters.insert().values(name=name, value=len(ids)))
        with op.batch_alter_table(name) as batch:
            batch.alter_column("display_id", existing_type=sa.Integer(), nullable=False)
            batch.create_unique_constraint(f"uq_{name}_display_id", ["display_id"])

def downgrade():
    for name in ("services", "categories"):
        with op.batch_alter_table(name) as batch:
            batch.drop_constraint(f"uq_{name}_display_id", type_="unique")
            batch.drop_column("display_id")
    op.drop_table("catalog_sequences")
