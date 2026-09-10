"""Transactional counters independent of database auto-increment allocation."""
from sqlalchemy import Column, Integer, String, Table, event, select, update
from app.db.base import Base

catalog_sequences = Table(
    "catalog_sequences", Base.metadata,
    Column("name", String(30), primary_key=True),
    Column("value", Integer, nullable=False),
)

@event.listens_for(catalog_sequences, "after_create")
def initialize_sequences(target, connection, **kwargs):
    connection.execute(target.insert(), [{"name": "categories", "value": 0}, {"name": "services", "value": 0}])

def assign_catalog_number(mapper, connection, target):
    # UPDATE locks this counter until the surrounding insert transaction commits.
    counter = catalog_sequences.c.name == target.__tablename__
    result = connection.execute(update(catalog_sequences).where(counter).values(value=catalog_sequences.c.value + 1))
    if result.rowcount != 1:
        raise RuntimeError("Catalog counter missing; run alembic upgrade head")
    target.display_id = connection.scalar(select(catalog_sequences.c.value).where(counter))
