import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category import Category
from app.models.service import Service
from app.schemas.service import ServiceRead
from app.services.catalog_validation import validate_catalog_values, resolve_staff


@pytest.fixture
def db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(Category(id=7, external_id=70, name='Care', slug='care'))
        session.commit()
        yield session
    engine.dispose()


def test_database_id_is_used_even_when_external_ids_differ(db):
    validate_catalog_values(db, Service, {'category_id': 7})
    with pytest.raises(HTTPException) as error:
        validate_catalog_values(db, Service, {'category_id': 70})
    assert error.value.status_code == 422
    service = Service(category_id=7, name='Visit', slug='visit')
    db.add(service)
    db.commit()
    result = ServiceRead.model_validate(service)
    assert result.category_id == 7
    assert result.category_name == 'Care'


@pytest.mark.parametrize('values', [{'external_id': 70}, {'slug': 'care'}, {'name': 'Care'}])
def test_category_duplicates_and_self_updates(db, values):
    with pytest.raises(HTTPException) as error:
        validate_catalog_values(db, Category, values)
    assert error.value.status_code == 409
    validate_catalog_values(db, Category, values, record_id=7)


def test_service_duplicates(db):
    db.add(Service(category_id=7, external_id=80, name='Visit', slug='visit'))
    db.commit()
    for values in ({'external_id': 80}, {'slug': 'visit'}):
        with pytest.raises(HTTPException) as error:
            validate_catalog_values(db, Service, values)
        assert error.value.status_code == 409


@pytest.mark.parametrize('values', [{'category_id': None}, {'name': None}, {'slug': ''}, {'currency': None}])
def test_invalid_updates(db, values):
    with pytest.raises(HTTPException) as error:
        validate_catalog_values(db, Service, values)
    assert error.value.status_code == 422


def test_unknown_staff_is_rejected(db):
    assert resolve_staff(db, []) == []
    with pytest.raises(HTTPException) as error:
        resolve_staff(db, [9999])
    assert error.value.status_code == 422


def test_persistent_numbers_ignore_large_database_ids_and_deletions(db):
    existing = db.get(Category, 7)
    assert existing.display_id == 1
    added = Category(id=30001, name='New', slug='new')
    db.add(added)
    db.commit()
    assert added.display_id == 2
    db.delete(added)
    db.commit()
    next_category = Category(id=60001, name='Next', slug='next')
    db.add(next_category)
    db.commit()
    assert next_category.display_id == 3
    first = Service(id=30001, category_id=7, name='First', slug='first')
    second = Service(id=60001, category_id=7, name='Second', slug='second')
    db.add_all([first, second])
    db.commit()
    assert (first.display_id, second.display_id) == (1, 2)
    assert db.get(Category, 7).display_id == 1


def test_rolled_back_creation_does_not_consume_number(db):
    category = Category(name='Rollback', slug='rollback')
    db.add(category)
    db.flush()
    allocated = category.display_id
    db.rollback()
    replacement = Category(name='Replacement', slug='replacement')
    db.add(replacement)
    db.commit()
    assert replacement.display_id == allocated


def test_migration_backfills_large_ids_without_changing_relationships():
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    path = Path(__file__).parents[1] / 'migrations/versions/20260910_0006_catalog_numbers.py'
    spec = importlib.util.spec_from_file_location('catalog_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE categories (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE services (id INTEGER PRIMARY KEY, category_id INTEGER REFERENCES categories(id))'))
        for record_id in [1, 2, 3, 4, 5, 6, 7, 30001]:
            connection.execute(text('INSERT INTO categories (id) VALUES (:id)'), {'id': record_id})
        connection.execute(text('INSERT INTO services (id, category_id) VALUES (30001, 30001)'))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        assert connection.execute(text('SELECT display_id FROM categories WHERE id=30001')).scalar_one() == 8
        assert connection.execute(text('SELECT display_id, category_id FROM services')).one() == (1, 30001)
        assert connection.execute(text("SELECT value FROM catalog_sequences WHERE name='categories'")).scalar_one() == 8
        migration.upgrade()  # A completed upgrade can safely run again.
        assert connection.execute(text("SELECT value FROM catalog_sequences WHERE name='categories'")).scalar_one() == 8
        migration.downgrade()
        assert connection.execute(text('SELECT category_id FROM services')).scalar_one() == 30001
    engine.dispose()


@pytest.mark.parametrize('partial_columns', [False, True])
def test_migration_resumes_existing_counter_table(partial_columns):
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    path = Path(__file__).parents[1] / 'migrations/versions/20260910_0006_catalog_numbers.py'
    spec = importlib.util.spec_from_file_location('resume_migration', path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine('sqlite:///:memory:')
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE catalog_sequences (name VARCHAR(30) PRIMARY KEY, value INTEGER NOT NULL)'))
        connection.execute(text('CREATE TABLE categories (id INTEGER PRIMARY KEY)'))
        connection.execute(text('CREATE TABLE services (id INTEGER PRIMARY KEY)'))
        connection.execute(text('INSERT INTO categories (id) VALUES (1), (30001)'))
        connection.execute(text('INSERT INTO services (id) VALUES (30001)'))
        if partial_columns:
            connection.execute(text('ALTER TABLE categories ADD COLUMN display_id INTEGER'))
            connection.execute(text('UPDATE categories SET display_id=1 WHERE id=1'))
            connection.execute(text("INSERT INTO catalog_sequences VALUES ('categories', 5)"))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        expected = 6 if partial_columns else 2
        assert connection.execute(text('SELECT display_id FROM categories WHERE id=30001')).scalar_one() == expected
        assert connection.execute(text('SELECT display_id FROM categories WHERE id=1')).scalar_one() == 1
        assert connection.execute(text('SELECT display_id FROM services')).scalar_one() == 1
        migration.upgrade()
        assert connection.execute(text("SELECT value FROM catalog_sequences WHERE name='categories'")).scalar_one() == expected
    engine.dispose()
