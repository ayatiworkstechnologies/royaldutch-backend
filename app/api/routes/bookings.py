from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_admin
from app.models.booking import Booking
from app.models.enums import MailStatus
from app.schemas.booking import BookingCreate, BookingDetail, BookingRead, BookingStatusUpdate, BookingUpdate
from app.services.booking_service import available_slots, create_booking, update_booking
from app.services.mail_service import create_booking_mail, template_for_status

router = APIRouter(prefix="/bookings", tags=["bookings"])


def to_booking_detail(booking: Booking) -> BookingDetail:
    detail = BookingDetail.model_validate(booking)
    detail.service_name = booking.service.name if booking.service else None
    detail.staff_name = booking.staff.name if booking.staff else None
    return detail


@router.post("", response_model=BookingRead)
def create_patient_booking(data: BookingCreate, db: DbSession) -> Booking:
    return create_booking(db, data)


@router.get("", response_model=list[BookingDetail], dependencies=[Depends(get_current_admin)])
def list_bookings(
    db: DbSession,
    status: str | None = Query(default=None),
    booking_date: date | None = Query(default=None),
) -> list[BookingDetail]:
    query = select(Booking).options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    if status:
        query = query.where(Booking.status == status)
    if booking_date:
        query = query.where(Booking.booking_date == booking_date)
    bookings = db.scalars(query.order_by(Booking.booking_date.desc(), Booking.booking_time.desc())).unique().all()
    return [to_booking_detail(booking) for booking in bookings]


@router.get("/slots")
def get_available_slots(
    db: DbSession,
    service_id: int = Query(...),
    selected_date: date = Query(...),
    staff_id: int | None = Query(default=None),
) -> dict:
    return {"slots": available_slots(db, service_id, selected_date, staff_id)}


@router.get("/lookup", response_model=list[BookingDetail])
def lookup_patient_bookings(db: DbSession, phone: str = Query(...)) -> list[BookingDetail]:
    bookings = db.scalars(
        select(Booking)
        .join(Booking.patient)
        .where(Booking.patient.has(phone=phone))
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
        .order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
    ).unique().all()
    return [to_booking_detail(booking) for booking in bookings]


@router.get("/calendar", response_model=list[BookingDetail], dependencies=[Depends(get_current_admin)])
def calendar_bookings(
    db: DbSession,
    start_date: date = Query(...),
    end_date: date = Query(...),
    staff_id: int | None = Query(default=None),
) -> list[BookingDetail]:
    query = (
        select(Booking)
        .where(Booking.booking_date >= start_date, Booking.booking_date <= end_date)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
        .order_by(Booking.booking_date, Booking.booking_time)
    )
    if staff_id:
        query = query.where(Booking.staff_id == staff_id)
    bookings = db.scalars(query).unique().all()
    return [to_booking_detail(booking) for booking in bookings]


@router.get("/{booking_id}", response_model=BookingDetail, dependencies=[Depends(get_current_admin)])
def get_booking(booking_id: int, db: DbSession) -> BookingDetail:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return to_booking_detail(booking)


@router.patch("/{booking_id}", response_model=BookingRead, dependencies=[Depends(get_current_admin)])
def patch_booking(booking_id: int, data: BookingUpdate, db: DbSession) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return update_booking(db, booking, data)


@router.patch("/{booking_id}/status", response_model=BookingRead, dependencies=[Depends(get_current_admin)])
def update_booking_status(booking_id: int, data: BookingStatusUpdate, db: DbSession) -> Booking:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = data.status
    template = template_for_status(data.status)
    if template:
        mail = create_booking_mail(booking, template)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/mail/{template}", dependencies=[Depends(get_current_admin)])
def queue_booking_mail(booking_id: int, template: str, db: DbSession) -> dict:
    allowed_templates = {"created", "confirmed", "cancelled", "completed", "reminder"}
    if template not in allowed_templates:
        raise HTTPException(status_code=400, detail="Unknown mail template")
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    mail = create_booking_mail(booking, template, MailStatus.queued)
    if not mail:
        raise HTTPException(status_code=400, detail="Patient email is missing")
    db.add(mail)
    db.commit()
    return {"message": "Mail queued", "template": template}
