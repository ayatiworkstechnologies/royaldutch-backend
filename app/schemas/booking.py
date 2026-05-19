from datetime import date, time
from decimal import Decimal

from app.models.enums import BookingStatus
from app.schemas.common import ORMModel, Timestamped
from app.schemas.patient import PatientCreate, PatientRead


class BookingCreate(ORMModel):
    service_id: int
    staff_id: int | None = None
    booking_date: date
    booking_time: time
    patient: PatientCreate
    notes: str | None = None
    first_visit: bool = True


class BookingUpdate(ORMModel):
    staff_id: int | None = None
    booking_date: date | None = None
    booking_time: time | None = None
    status: BookingStatus | None = None
    notes: str | None = None


class BookingStatusUpdate(ORMModel):
    status: BookingStatus


class BookingRead(Timestamped):
    id: int
    booking_code: str
    patient_id: int
    service_id: int
    staff_id: int | None
    booking_date: date
    booking_time: time
    duration_minutes: int | None
    price: Decimal | None
    currency: str
    status: BookingStatus
    notes: str | None
    first_visit: bool


class BookingDetail(BookingRead):
    patient: PatientRead
    service_name: str | None = None
    staff_name: str | None = None
