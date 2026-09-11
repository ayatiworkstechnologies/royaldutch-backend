import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.category import Category
from app.models.service import Service
from app.models.sub_service import SubService
from app.models.enums import RecordStatus
from app.schemas.sub_service import SubServiceCreate, SubServiceUpdate, SubServiceRead
from app.api.routes.sub_services import create_sub_service, update_sub_service, delete_sub_service, list_sub_services


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        category = Category(name="Care", slug="care")
        session.add(category)
        session.flush()
        session.add_all([Service(category_id=category.id, name="Care", slug="care"), Service(category_id=category.id, name="Visit", slug="visit")])
        session.commit()
        yield session
    engine.dispose()


def create(db, parent=1):
    return create_sub_service(parent, SubServiceCreate(name="Nursing", slug="nursing", price="10.50"), db, None, None)


def test_crud_and_parent_scoping(db):
    child = create(db)
    assert SubServiceRead.model_validate(child).service_id == 1
    assert list_sub_services(1, db, False) == [child]
    with pytest.raises(HTTPException) as error:
        update_sub_service(2, child.id, SubServiceUpdate(name="Wrong"), db, None, None)
    assert error.value.status_code == 404
    update_sub_service(1, child.id, SubServiceUpdate(status="inactive", price=None), db, None, None)
    assert child.price is None
    assert list_sub_services(1, db, False) == []
    assert list_sub_services(1, db, True) == [child]
    delete_sub_service(1, child.id, db, None, None)
    assert list_sub_services(1, db, True) == []


def test_duplicates_are_scoped_to_parent(db):
    create(db)
    with pytest.raises(HTTPException) as error:
        create(db)
    assert error.value.status_code == 409
    assert create(db, 2).service_id == 2


def test_parent_visibility_and_deletion(db):
    create(db)
    parent = db.get(Service, 1)
    parent.status = RecordStatus.inactive
    db.commit()
    with pytest.raises(HTTPException) as error:
        list_sub_services(1, db, False)
    assert error.value.status_code == 404
    assert len(list_sub_services(1, db, True)) == 1
    db.delete(parent)
    db.commit()
    assert db.scalar(select(SubService)) is None
    with pytest.raises(HTTPException):
        create(db, 999)


@pytest.mark.parametrize("values", [{"name": " "}, {"name": None}, {"status": None}, {"price": -1}, {"duration_minutes": 0}])
def test_invalid_updates(values):
    with pytest.raises(ValidationError):
        SubServiceUpdate(**values)
