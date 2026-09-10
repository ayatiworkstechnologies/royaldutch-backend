"""Persist sequential category and service display IDs."""
from alembic import op
import sqlalchemy as sa

revision = "20260910_0006"
down_revision = "89e04b0aba1f"
branch_labels = None
depends_on = None

def upgrade():
    connection = op.get_bind()
    # MySQL DDL may survive a failed upgrade without advancing alembic_version.
    if not sa.inspect(connection).has_table("catalog_sequences"):
        op.create_table("catalog_sequences",
            sa.Column("name", sa.String(30), primary_key=True),
            sa.Column("value", sa.Integer(), nullable=False))
    counters = sa.table("catalog_sequences", sa.column("name", sa.String()), sa.column("value", sa.Integer()))
    for name in ("categories", "services"):
        columns = {column["name"]: column for column in sa.inspect(connection).get_columns(name)}
        if "display_id" not in columns:
            op.add_column(name, sa.Column("display_id", sa.Integer(), nullable=True))
        table = sa.table(name, sa.column("id", sa.Integer()), sa.column("display_id", sa.Integer()))
        rows = connection.execute(sa.select(table.c.id, table.c.display_id).order_by(table.c.id)).all()
        assigned = [number for _, number in rows if number is not None]
        if any(number <= 0 for number in assigned) or len(assigned) != len(set(assigned)):
            raise RuntimeError(f"{name} contains invalid or duplicate display_id values; resolve these before retrying")
        previous = connection.scalar(sa.select(counters.c.value).where(counters.c.name == name))
        number = max([previous or 0, *assigned])
        for record_id, existing in rows:
            if existing is None:
                number += 1
                connection.execute(table.update().where(table.c.id == record_id).values(display_id=number))
        if previous is None:
            connection.execute(counters.insert().values(name=name, value=number))
        else:
            connection.execute(counters.update().where(counters.c.name == name).values(value=number))
        inspector = sa.inspect(connection)
        unique = any(item.get("column_names") == ["display_id"] for item in inspector.get_unique_constraints(name))
        unique = unique or any(item.get("unique") and item.get("column_names") == ["display_id"] for item in inspector.get_indexes(name))
        nullable = next(column["nullable"] for column in inspector.get_columns(name) if column["name"] == "display_id")
        if nullable or not unique:
            with op.batch_alter_table(name) as batch:
                if nullable:
                    batch.alter_column("display_id", existing_type=sa.Integer(), nullable=False)
                if not unique:
                    batch.create_unique_constraint(f"uq_{name}_display_id", ["display_id"])

def downgrade():
    for name in ("services", "categories"):
        with op.batch_alter_table(name) as batch:
            batch.drop_constraint(f"uq_{name}_display_id", type_="unique")
            batch.drop_column("display_id")
    op.drop_table("catalog_sequences")
