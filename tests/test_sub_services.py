import pytest
from datetime import date, timedelta
from decimal import Decimal
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
from app.schemas.booking import BookingCreate
from app.services.booking_service import create_booking


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


def booking_data(ids):
    return BookingCreate(service_id=1, sub_service_ids=ids,
        booking_date=date.today() + timedelta(days=1), booking_time="10:00",
        patient={"full_name": "Upgrade Patient", "phone": "+971501234567"}, notes="Patient request")


def test_booking_upgrade_total_and_snapshot(db):
    child = create(db)
    db.get(Service, 1).price = Decimal("100.00")
    db.commit()
    booking = create_booking(db, booking_data([child.id, child.id]))
    assert booking.price == Decimal("110.50")
    assert "Patient request" in booking.notes
    assert booking.notes.count("Nursing") == 1
    assert "AED 10.50" in booking.notes


def test_price_range_is_stored_and_makes_booking_total_on_request(db):
    child = create_sub_service(
        1,
        SubServiceCreate(name="Home visit", slug="home-visit", price="200-500"),
        db,
        None,
        None,
    )
    db.get(Service, 1).price = Decimal("100.00")
    db.commit()

    assert child.price == "200-500"
    assert SubServiceRead.model_validate(child).price == "200-500"
    booking = create_booking(db, booking_data([child.id]))
    assert booking.price is None
    assert "AED 200-500" in booking.notes


@pytest.mark.parametrize("invalid", ["parent", "inactive", "currency", "missing"])
def test_booking_rejects_invalid_upgrade(db, invalid):
    child = create(db, 2 if invalid == "parent" else 1)
    if invalid == "inactive":
        child.status = RecordStatus.inactive
    if invalid == "currency":
        child.currency = "USD"
    db.commit()
    with pytest.raises(HTTPException) as error:
        create_booking(db, booking_data([9999 if invalid == "missing" else child.id]))
    assert error.value.status_code == 422


def test_unpriced_upgrade_keeps_total_on_request(db):
    child = create(db)
    child.price = None
    db.get(Service, 1).price = Decimal("100.00")
    db.commit()
    booking = create_booking(db, booking_data([child.id]))
    assert booking.price is None
    assert "Price on request" in booking.notes


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


@pytest.mark.parametrize("values", [{"name": " "}, {"name": None}, {"status": None}, {"price": -1}, {"price": "500-200"}, {"price": "200-x"}, {"duration_minutes": 0}])
def test_invalid_updates(values):
    with pytest.raises(ValidationError):
        SubServiceUpdate(**values)
