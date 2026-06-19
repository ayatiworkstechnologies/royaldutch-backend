from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.staff import Staff
from app.models.user import User
from app.schemas.booking import BookingDetail, BookingStatusUpdate, BookingRead
from app.services.booking_service import update_booking_status as set_booking_status
from app.services.mail_service import create_booking_mail, template_for_status

router = APIRouter(prefix="/staff/me", tags=["staff dashboard"])

CLINICAL_ROLES = {"doctor", "nurse", "physiotherapist", "dentist", "laser_specialist", "facial_therapist"}


def _require_clinical(user: User = Depends(get_current_user)) -> User:
    if user.role not in CLINICAL_ROLES:
        raise HTTPException(status_code=403, detail="Clinical staff only")
    return user


def _to_detail(b: Booking) -> BookingDetail:
    detail = BookingDetail.model_validate(b)
    detail.service_name = b.service.name if b.service else None
    detail.staff_name = b.staff.name if b.staff else None
    return detail


@router.get("/bookings", response_model=list[BookingDetail])
def my_staff_bookings(
    db: DbSession,
    booking_date: date | None = Query(default=None),
    status: BookingStatus | None = Query(default=None),
    user: User = Depends(_require_clinical),
) -> list[BookingDetail]:
    if not user.staff_id:
        return []
    query = (
        select(Booking)
        .where(Booking.staff_id == user.staff_id)
        .options(
            joinedload(Booking.patient),
            joinedload(Booking.service),
            joinedload(Booking.staff),
        )
        .order_by(Booking.booking_date.desc(), Booking.booking_time.asc())
    )
    if booking_date:
        query = query.where(Booking.booking_date == booking_date)
    if status:
        query = query.where(Booking.status == status)
    return [_to_detail(b) for b in db.scalars(query).unique().all()]


@router.patch("/bookings/{booking_id}/status", response_model=BookingRead)
def update_my_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    db: DbSession,
    user: User = Depends(_require_clinical),
) -> Booking:
    if not user.staff_id:
        raise HTTPException(status_code=403, detail="No staff profile linked to this account")
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id, Booking.staff_id == user.staff_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    set_booking_status(db, booking, data.status)
    template = template_for_status(data.status)
    if template:
        mail = create_booking_mail(booking, template, db=db)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(booking)
    return booking
