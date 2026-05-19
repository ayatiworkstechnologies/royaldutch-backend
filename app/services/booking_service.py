from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking
from app.models.enums import BookingStatus, RecordStatus
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.mail_service import create_booking_mail

BLOCKING_STATUSES = {
    BookingStatus.pending,
    BookingStatus.confirmed,
    BookingStatus.rescheduled,
}


def make_booking_code(db: Session, booking_date: date) -> str:
    prefix = f"RD-{booking_date:%y%m%d}-"
    existing_codes = db.scalars(
        select(Booking.booking_code).where(Booking.booking_code.like(f"{prefix}%"))
    ).all()
    numbers = []
    for code in existing_codes:
        try:
            numbers.append(int(code.rsplit("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    next_number = (max(numbers) if numbers else 0) + 1
    return f"{prefix}{next_number:04d}"


def get_or_create_patient(db: Session, data) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.phone == data.phone))
    if patient:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        return patient

    patient = Patient(**data.model_dump())
    db.add(patient)
    db.flush()
    return patient


def find_staff_for_booking(
    db: Session,
    service_id: int,
    booking_date: date,
    booking_time: time,
    preferred_staff_id: int | None,
) -> Staff:
    query = (
        select(Staff)
        .join(Staff.services)
        .where(Staff.status == RecordStatus.active, Service.id == service_id)
        .options(joinedload(Staff.availability))
    )
    if preferred_staff_id:
        query = query.where(Staff.id == preferred_staff_id)

    staff_candidates = db.scalars(query).unique().all()
    for staff in staff_candidates:
        if slot_is_available(db, staff.id, booking_date, booking_time):
            return staff

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="No available specialist found for the selected slot",
    )


def slot_is_available(db: Session, staff_id: int, booking_date: date, booking_time: time) -> bool:
    if booking_date < date.today():
        return False

    day_of_week = booking_date.weekday()
    availability = db.scalar(
        select(StaffAvailability).where(
            StaffAvailability.staff_id == staff_id,
            StaffAvailability.day_of_week == day_of_week,
            StaffAvailability.status == RecordStatus.active,
        )
    )
    if not availability:
        return False

    if booking_time < availability.start_time or booking_time >= availability.end_time:
        return False

    if availability.break_start_time and availability.break_end_time:
        if availability.break_start_time <= booking_time < availability.break_end_time:
            return False

    existing = db.scalar(
        select(Booking).where(
            Booking.staff_id == staff_id,
            Booking.booking_date == booking_date,
            Booking.booking_time == booking_time,
            Booking.status.in_(BLOCKING_STATUSES),
        )
    )
    return existing is None


def create_booking(db: Session, data: BookingCreate) -> Booking:
    service = db.get(Service, data.service_id)
    if not service or service.status != RecordStatus.active:
        raise HTTPException(status_code=404, detail="Service not found or inactive")

    staff = find_staff_for_booking(db, service.id, data.booking_date, data.booking_time, data.staff_id)
    patient = get_or_create_patient(db, data.patient)

    booking = Booking(
        booking_code=make_booking_code(db, data.booking_date),
        patient_id=patient.id,
        service_id=service.id,
        staff_id=staff.id,
        booking_date=data.booking_date,
        booking_time=data.booking_time,
        duration_minutes=service.duration_minutes,
        price=service.price,
        currency=service.currency,
        notes=data.notes,
        first_visit=data.first_visit,
        status=BookingStatus.pending,
    )
    db.add(booking)
    db.flush()
    db.add(
        Notification(
            booking_id=booking.id,
            channel="dashboard",
            recipient="admin",
            subject="New appointment request",
            message=f"New booking request {booking.booking_code} received.",
        )
    )
    mail = create_booking_mail(booking, "created")
    if mail:
        db.add(mail)
    db.commit()
    db.refresh(booking)
    return booking


def update_booking(db: Session, booking: Booking, data: BookingUpdate) -> Booking:
    update_data = data.model_dump(exclude_unset=True)
    booking_date = update_data.get("booking_date", booking.booking_date)
    booking_time = update_data.get("booking_time", booking.booking_time)
    staff_id = update_data.get("staff_id", booking.staff_id)

    if {"booking_date", "booking_time", "staff_id"} & update_data.keys():
        if staff_id is None or not slot_is_available(db, staff_id, booking_date, booking_time):
            raise HTTPException(status_code=409, detail="Selected slot is not available")

    for field, value in update_data.items():
        setattr(booking, field, value)
    db.commit()
    db.refresh(booking)
    return booking


def available_slots(db: Session, service_id: int, selected_date: date, staff_id: int | None = None) -> list[str]:
    if selected_date < date.today():
        return []

    staff_query = (
        select(Staff)
        .join(Staff.services)
        .where(Staff.status == RecordStatus.active, Service.id == service_id)
    )
    if staff_id:
        staff_query = staff_query.where(Staff.id == staff_id)

    slots: set[str] = set()
    for staff in db.scalars(staff_query).unique().all():
        availability = db.scalar(
            select(StaffAvailability).where(
                StaffAvailability.staff_id == staff.id,
                StaffAvailability.day_of_week == selected_date.weekday(),
                StaffAvailability.status == RecordStatus.active,
            )
        )
        if not availability:
            continue

        cursor = datetime.combine(selected_date, availability.start_time)
        end_at = datetime.combine(selected_date, availability.end_time)
        while cursor < end_at:
            slot_time = cursor.time()
            if slot_is_available(db, staff.id, selected_date, slot_time):
                slots.add(slot_time.strftime("%H:%M"))
            cursor += timedelta(minutes=30)

    return sorted(slots)


def dashboard_stats(db: Session) -> dict:
    today = date.today()
    count_status = lambda status_value: db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == status_value)
    )
    revenue = db.scalar(
        select(func.coalesce(func.sum(Booking.price), 0)).where(Booking.status == BookingStatus.completed)
    )
    most_booked = db.execute(
        select(Service.name, func.count(Booking.id).label("count"))
        .join(Booking, Booking.service_id == Service.id)
        .group_by(Service.id)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
    ).all()

    return {
        "todays_bookings": db.scalar(
            select(func.count()).select_from(Booking).where(Booking.booking_date == today)
        ),
        "pending_bookings": count_status(BookingStatus.pending),
        "confirmed_bookings": count_status(BookingStatus.confirmed),
        "completed_bookings": count_status(BookingStatus.completed),
        "cancelled_bookings": count_status(BookingStatus.cancelled),
        "total_revenue": revenue,
        "most_booked_services": [{"service": name, "count": count} for name, count in most_booked],
    }
