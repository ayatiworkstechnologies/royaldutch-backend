from datetime import date, time
from decimal import Decimal

from pydantic import model_validator

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

    @model_validator(mode="after")
    def validate_requested_slot(self) -> "BookingCreate":
        if self.booking_date < date.today():
            raise ValueError("Booking date cannot be in the past")
        if self.booking_time.second or self.booking_time.microsecond:
            raise ValueError("Booking time must not include seconds")
        return self


class BookingUpdate(ORMModel):
    staff_id: int | None = None
    booking_date: date | None = None
    booking_time: time | None = None
    status: BookingStatus | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_requested_slot(self) -> "BookingUpdate":
        if self.booking_date and self.booking_date < date.today():
            raise ValueError("Booking date cannot be in the past")
        if self.booking_time and (self.booking_time.second or self.booking_time.microsecond):
            raise ValueError("Booking time must not include seconds")
        return self


class BookingStatusUpdate(ORMModel):
    status: BookingStatus
    notes: str | None = None


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
