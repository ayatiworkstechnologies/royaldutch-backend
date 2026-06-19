from datetime import date, datetime, time, timedelta
from contextlib import contextmanager
from decimal import Decimal
from threading import RLock

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking, BookingSlotLock
from app.models.billing import Invoice
from app.models.enums import BookingStatus, InvoiceStatus, PaymentStatus, RecordStatus, UserRole
from app.models.notification import Notification
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.mail_service import create_booking_mail

BLOCKING_STATUSES = {
    BookingStatus.pending,
    BookingStatus.confirmed,
    BookingStatus.rescheduled,
}
DEFAULT_SLOT_MINUTES = 30
TERMINAL_STATUSES = {
    BookingStatus.completed,
    BookingStatus.cancelled,
    BookingStatus.no_show,
}
ALLOWED_STATUS_TRANSITIONS = {
    BookingStatus.pending: {
        BookingStatus.pending,
        BookingStatus.confirmed,
        BookingStatus.cancelled,
        BookingStatus.rescheduled,
    },
    BookingStatus.confirmed: {
        BookingStatus.confirmed,
        BookingStatus.completed,
        BookingStatus.cancelled,
        BookingStatus.no_show,
        BookingStatus.rescheduled,
    },
    BookingStatus.rescheduled: {
        BookingStatus.rescheduled,
        BookingStatus.confirmed,
        BookingStatus.completed,
        BookingStatus.cancelled,
        BookingStatus.no_show,
    },
    BookingStatus.completed: {BookingStatus.completed},
    BookingStatus.cancelled: {BookingStatus.cancelled},
    BookingStatus.no_show: {BookingStatus.no_show},
}
_booking_locks: dict[tuple[int, date], RLock] = {}
_booking_locks_guard = RLock()


@contextmanager
def staff_date_booking_lock(staff_id: int, booking_date: date):
    key = (staff_id, booking_date)
    with _booking_locks_guard:
        lock = _booking_locks.setdefault(key, RLock())
    with lock:
        yield


def service_duration_minutes(service: Service | None) -> int:
    if service and service.duration_minutes and service.duration_minutes > 0:
        return service.duration_minutes
    return DEFAULT_SLOT_MINUTES


def validate_status_transition(current: BookingStatus, new: BookingStatus) -> None:
    if new not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change booking status from {current} to {new}",
        )


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


def is_unique_booking_code_error(exc: IntegrityError) -> bool:
    text = str(exc.orig).lower()
    return "booking_code" in text or "bookings.booking_code" in text


def slot_lock_key(staff_id: int, booking_date: date, booking_time: time) -> str:
    return f"{staff_id}:{booking_date.isoformat()}:{booking_time.isoformat()}"


def acquire_booking_slot_lock(
    db: Session,
    staff_id: int,
    booking_date: date,
    booking_time: time,
    booking_id: int | None = None,
) -> BookingSlotLock:
    lock = BookingSlotLock(
        staff_id=staff_id,
        booking_date=booking_date,
        booking_time=booking_time,
        lock_key=slot_lock_key(staff_id, booking_date, booking_time),
        booking_id=booking_id,
    )
    db.add(lock)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        text = str(exc.orig).lower()
        if "booking_slot" in text or "uq_booking_slot_lock" in text or "lock_key" in text:
            raise HTTPException(status_code=409, detail="Selected slot is not available") from exc
        raise
    return lock


def release_booking_slot_lock(db: Session, booking: Booking) -> None:
    if not booking.staff_id:
        return
    lock = db.scalar(select(BookingSlotLock).where(BookingSlotLock.booking_id == booking.id))
    if lock:
        db.delete(lock)


def sync_booking_slot_lock(db: Session, booking: Booking, status_value: BookingStatus) -> None:
    existing_lock = db.scalar(select(BookingSlotLock).where(BookingSlotLock.booking_id == booking.id))
    should_lock = status_value in BLOCKING_STATUSES and booking.staff_id is not None
    if not should_lock:
        if existing_lock:
            db.delete(existing_lock)
        return

    desired_key = slot_lock_key(booking.staff_id, booking.booking_date, booking.booking_time)
    if existing_lock and existing_lock.lock_key == desired_key:
        return
    if existing_lock:
        db.delete(existing_lock)
        db.flush()
    acquire_booking_slot_lock(db, booking.staff_id, booking.booking_date, booking.booking_time, booking.id)

def get_or_create_patient(db: Session, data) -> Patient:
    patient = db.scalar(select(Patient).where(Patient.phone == data.phone))
    if patient:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
    else:
        patient = Patient(**data.model_dump())
        db.add(patient)
        db.flush()

    if patient.email and not patient.user_id:
        user = db.scalar(select(User).where(User.email == patient.email))
        if not user:
            user = User(
                name=patient.full_name,
                email=patient.email,
                role=UserRole.customer,
                hashed_password=None,
            )
            db.add(user)
            db.flush()
        patient.user_id = user.id

    return patient


def find_staff_for_booking(
    db: Session,
    service_id: int,
    booking_date: date,
    booking_time: time,
    preferred_staff_id: int | None,
) -> Staff | None:
    """
    Return the best available staff member for this slot, or None if no staff
    is configured yet (admin assigns later).  Never raises a 409 — slot
    availability is now gated by clinic hours, not individual staff schedules.
    """
    query = (
        select(Staff)
        .join(Staff.services)
        .where(Staff.status == RecordStatus.active, Service.id == service_id)
        .options(joinedload(Staff.availability))
    )
    if preferred_staff_id:
        query = query.where(Staff.id == preferred_staff_id)

    service = db.get(Service, service_id)
    staff_candidates = db.scalars(query).unique().all()
    if not staff_candidates:
        return None  # no staff configured — admin will assign later

    duration = service_duration_minutes(service) if service else DEFAULT_SLOT_MINUTES
    for staff in staff_candidates:
        if slot_is_available(db, staff.id, booking_date, booking_time, duration):
            return staff

    # All staff busy at this slot — still allow the booking, admin assigns later
    return None


def slot_is_available(
    db: Session,
    staff_id: int,
    booking_date: date,
    booking_time: time,
    duration_minutes: int = DEFAULT_SLOT_MINUTES,
    exclude_booking_id: int | None = None,
) -> bool:
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

    slot_start = datetime.combine(booking_date, booking_time)
    slot_end = slot_start + timedelta(minutes=duration_minutes)
    work_start = datetime.combine(booking_date, availability.start_time)
    work_end = datetime.combine(booking_date, availability.end_time)
    if slot_start < work_start or slot_end > work_end:
        return False

    if availability.break_start_time and availability.break_end_time:
        break_start = datetime.combine(booking_date, availability.break_start_time)
        break_end = datetime.combine(booking_date, availability.break_end_time)
        if slot_start < break_end and slot_end > break_start:
            return False

    conflict_query = select(Booking).where(
        Booking.staff_id == staff_id,
        Booking.booking_date == booking_date,
        Booking.status.in_(BLOCKING_STATUSES),
    )
    if exclude_booking_id:
        conflict_query = conflict_query.where(Booking.id != exclude_booking_id)

    for existing in db.scalars(conflict_query).all():
        existing_start = datetime.combine(existing.booking_date, existing.booking_time)
        existing_end = existing_start + timedelta(minutes=existing.duration_minutes or DEFAULT_SLOT_MINUTES)
        if slot_start < existing_end and slot_end > existing_start:
            return False
    return True


def ensure_booking_slot_available(
    db: Session,
    staff_id: int,
    booking_date: date,
    booking_time: time,
    duration_minutes: int,
    exclude_booking_id: int | None = None,
) -> None:
    if not slot_is_available(db, staff_id, booking_date, booking_time, duration_minutes, exclude_booking_id):
        raise HTTPException(status_code=409, detail="Selected slot is not available")


def ensure_booking_can_block_slot(db: Session, booking: Booking, status_value: BookingStatus) -> None:
    # Slot gating is now based on clinic hours, not staff availability.
    # Only block if another booking by the SAME staff overlaps this slot.
    if status_value in BLOCKING_STATUSES and booking.staff_id:
        conflict = db.scalar(
            select(Booking).where(
                Booking.id != booking.id,
                Booking.staff_id == booking.staff_id,
                Booking.booking_date == booking.booking_date,
                Booking.status.in_(BLOCKING_STATUSES),
            )
        )
        if conflict:
            cs = datetime.combine(conflict.booking_date, conflict.booking_time)
            ce = cs + timedelta(minutes=conflict.duration_minutes or DEFAULT_SLOT_MINUTES)
            bs = datetime.combine(booking.booking_date, booking.booking_time)
            be = bs + timedelta(minutes=booking.duration_minutes or DEFAULT_SLOT_MINUTES)
            if bs < ce and be > cs:
                raise HTTPException(
                    status_code=409,
                    detail=f"This doctor already has a booking at {booking.booking_time}",
                )


def create_booking(db: Session, data: BookingCreate) -> Booking:
    service = db.get(Service, data.service_id)
    if not service or service.status != RecordStatus.active:
        raise HTTPException(status_code=404, detail="Service not found or inactive")

    # Auto-assign best available staff — may return None (admin assigns later)
    staff = find_staff_for_booking(db, service.id, data.booking_date, data.booking_time, data.staff_id)
    patient = get_or_create_patient(db, data.patient)

    for _ in range(3):
        booking = Booking(
            booking_code=make_booking_code(db, data.booking_date),
            patient_id=patient.id,
            service_id=service.id,
            staff_id=staff.id if staff else None,
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
        try:
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
        except IntegrityError as exc:
            db.rollback()
            if not is_unique_booking_code_error(exc):
                raise
            patient = get_or_create_patient(db, data.patient)

    raise HTTPException(status_code=409, detail="Could not allocate booking code. Please retry.")


def update_booking(db: Session, booking: Booking, data: BookingUpdate) -> Booking:
    update_data = data.model_dump(exclude_unset=True)
    booking_date = update_data.get("booking_date", booking.booking_date)
    booking_time = update_data.get("booking_time", booking.booking_time)
    staff_id = update_data.get("staff_id", booking.staff_id)
    new_status = update_data.get("status", booking.status)

    # Only check slot conflict when date or time is actually changing,
    # not when admin is just assigning/reassigning a staff member.
    rescheduling = {"booking_date", "booking_time"} & update_data.keys()
    if rescheduling:
        if staff_id is not None:
            ensure_booking_slot_available(
                db,
                staff_id,
                booking_date,
                booking_time,
                booking.duration_minutes or DEFAULT_SLOT_MINUTES,
                booking.id,
            )
        if "status" not in update_data and booking.status not in TERMINAL_STATUSES:
            update_data["status"] = BookingStatus.rescheduled

    if "status" in update_data:
        validate_status_transition(booking.status, update_data["status"])
        new_status = update_data["status"]

    for field, value in update_data.items():
        setattr(booking, field, value)
    ensure_booking_can_block_slot(db, booking, new_status)
    sync_booking_slot_lock(db, booking, new_status)
    db.commit()
    db.refresh(booking)
    return booking


def update_booking_status(db: Session, booking: Booking, status_value: BookingStatus) -> Booking:
    validate_status_transition(booking.status, status_value)
    ensure_booking_can_block_slot(db, booking, status_value)
    booking.status = status_value
    sync_booking_slot_lock(db, booking, status_value)
    return booking


# ── Clinic default schedule (used when no staff constraints are needed) ───────
# Slots are generated from clinic hours; doctor is assigned by admin after booking.
_CLINIC_WORK_START  = time(9, 0)
_CLINIC_WORK_END    = time(18, 0)
_CLINIC_BREAK_START = time(13, 0)
_CLINIC_BREAK_END   = time(14, 0)
_CLINIC_WORK_DAYS   = {0, 1, 2, 3, 4, 5}  # Mon–Sat  (0=Mon … 6=Sun)


def _slots_for_date(
    d: date,
    booked_times: set[str],
    duration: int,
    now: datetime | None = None,
) -> dict[str, list[str]]:
    """
    Generate clinic-hour slots for `d` using the default schedule.
    `booked_times` = HH:MM strings already taken by any confirmed/pending booking
    for this service on this date.  No staff required.
    """
    if d.weekday() not in _CLINIC_WORK_DAYS:
        return {"free": [], "taken": []}

    work_start  = datetime.combine(d, _CLINIC_WORK_START)
    work_end    = datetime.combine(d, _CLINIC_WORK_END)
    break_start = datetime.combine(d, _CLINIC_BREAK_START)
    break_end   = datetime.combine(d, _CLINIC_BREAK_END)
    cutoff      = now if (now and d == now.date()) else None

    free: list[str] = []
    taken: list[str] = []
    cursor = work_start
    while cursor < work_end:
        slot_end = cursor + timedelta(minutes=duration)
        if slot_end > work_end:
            break
        # skip already-passed time today (30-min look-ahead buffer)
        if cutoff and cursor < cutoff + timedelta(minutes=30):
            cursor += timedelta(minutes=DEFAULT_SLOT_MINUTES)
            continue
        # skip lunch break
        if cursor < break_end and slot_end > break_start:
            cursor += timedelta(minutes=DEFAULT_SLOT_MINUTES)
            continue
        label = cursor.strftime("%H:%M")
        (taken if label in booked_times else free).append(label)
        cursor += timedelta(minutes=DEFAULT_SLOT_MINUTES)

    return {"free": free, "taken": taken}


def available_slots(db: Session, service_id: int, selected_date: date, staff_id: int | None = None) -> list[str]:
    """Return only free slot strings for a single date (legacy /slots endpoint)."""
    result = available_slots_range(db, service_id, selected_date, days=1)
    return result.get(selected_date.isoformat(), {}).get("free", [])


def available_slots_range(
    db: Session,
    service_id: int,
    start_date: date,
    days: int = 30,
    staff_id: int | None = None,  # kept for API compat, no longer used for slot gating
) -> dict[str, dict[str, list[str]]]:
    """
    Return {date_iso: {"free": [...], "taken": [...]}} for `days` days from start_date.
    Slots are based on clinic operating hours — no staff configuration required.
    A slot is 'taken' when an existing booking already occupies it for this service.
    Uses 2 DB queries total regardless of date range.
    """
    today = date.today()
    now   = datetime.now()
    all_dates = [start_date + timedelta(days=i) for i in range(days)]
    dates     = [d for d in all_dates if d >= today]
    empty: dict[str, list[str]] = {"free": [], "taken": []}
    result: dict[str, dict[str, list[str]]] = {d.isoformat(): dict(empty) for d in all_dates}

    if not dates:
        return result

    # 1. Validate service exists and is active
    service = db.get(Service, service_id)
    if not service or service.status != RecordStatus.active:
        return result

    # 2. Fetch existing bookings for this service across the date range (one query)
    bookings = db.scalars(
        select(Booking).where(
            Booking.service_id == service_id,
            Booking.booking_date >= dates[0],
            Booking.booking_date <= dates[-1],
            Booking.status.in_(BLOCKING_STATUSES),
        )
    ).all()
    booked_by_date: dict[date, set[str]] = {}
    for b in bookings:
        if b.booking_time:
            booked_by_date.setdefault(b.booking_date, set()).add(
                b.booking_time.strftime("%H:%M")
            )

    duration = service_duration_minutes(service)
    for d in dates:
        result[d.isoformat()] = _slots_for_date(
            d, booked_by_date.get(d, set()), duration, now
        )

    return result


def dashboard_stats(db: Session) -> dict:
    today = date.today()
    count_status = lambda status_value: db.scalar(
        select(func.count()).select_from(Booking).where(Booking.status == status_value)
    )
    booking_revenue = db.scalar(
        select(func.coalesce(func.sum(Booking.price), 0)).where(Booking.status == BookingStatus.completed)
    )
    invoice_revenue = db.scalar(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.status != InvoiceStatus.cancelled)
    )
    collected_revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.payment_status.in_({PaymentStatus.paid, PaymentStatus.partially_paid}))
    )
    refunded_revenue = db.scalar(
        select(func.coalesce(func.sum(Payment.refund_amount), 0)).where(Payment.refund_amount > 0)
    )
    net_revenue = collected_revenue - refunded_revenue
    booking_revenue = Decimal(str(booking_revenue or 0))
    invoice_revenue = Decimal(str(invoice_revenue or 0))
    collected_revenue = Decimal(str(collected_revenue or 0))
    refunded_revenue = Decimal(str(refunded_revenue or 0))
    net_revenue = Decimal(str(net_revenue or 0))
    most_booked = db.execute(
        select(Service.name, func.count(Booking.id).label("count"))
        .join(Booking, Booking.service_id == Service.id)
        .group_by(Service.id)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
    ).all()

    recent_bookings_rows = db.execute(
        select(
            Booking.id,
            Booking.booking_code,
            Booking.booking_date,
            Booking.booking_time,
            Booking.status,
            Booking.price,
            Booking.currency,
            Patient.full_name.label("patient_name"),
            Service.name.label("service_name"),
            Staff.name.label("staff_name"),
        )
        .join(Patient, Booking.patient_id == Patient.id)
        .join(Service, Booking.service_id == Service.id)
        .outerjoin(Staff, Booking.staff_id == Staff.id)
        .order_by(Booking.created_at.desc())
        .limit(10)
    ).all()

    recent_bookings = [
        {
            "id": row.id,
            "booking_code": row.booking_code,
            "booking_date": row.booking_date.isoformat() if row.booking_date else None,
            "booking_time": row.booking_time.isoformat() if row.booking_time else None,
            "status": str(row.status),
            "price": float(row.price) if row.price else 0,
            "currency": row.currency or "AED",
            "patient_name": row.patient_name,
            "service_name": row.service_name,
            "staff_name": row.staff_name,
        }
        for row in recent_bookings_rows
    ]

    return {
        "todays_bookings": db.scalar(
            select(func.count()).select_from(Booking).where(Booking.booking_date == today)
        ),
        "pending_bookings": count_status(BookingStatus.pending),
        "confirmed_bookings": count_status(BookingStatus.confirmed),
        "completed_bookings": count_status(BookingStatus.completed),
        "cancelled_bookings": count_status(BookingStatus.cancelled),
        "no_show_bookings": count_status(BookingStatus.no_show),
        "total_patients": db.scalar(select(func.count()).select_from(Patient)),
        "total_revenue": net_revenue,
        "booking_revenue": booking_revenue,
        "invoice_revenue": invoice_revenue,
        "collected_revenue": collected_revenue,
        "refunded_revenue": refunded_revenue,
        "net_revenue": net_revenue,
        "most_booked_services": [{"service": name, "count": count} for name, count in most_booked],
        "recent_bookings": recent_bookings,
    }
