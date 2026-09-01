from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.booking import Booking
from app.models.enums import BookingStatus, MailStatus
from app.schemas.booking import BookingCreate, BookingDetail, BookingRead, BookingStatusUpdate, BookingUpdate
from app.services.booking_service import available_slots, available_slots_range, create_booking, update_booking, update_booking_status as set_booking_status
from app.services.mail_service import create_booking_mail, template_for_status
from app.services.management_alert_service import send_booking_alerts
from app.services.audit_service import model_snapshot, write_audit_log
from app.models.user import User
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/bookings", tags=["bookings"])


def to_booking_detail(booking: Booking) -> BookingDetail:
    detail = BookingDetail.model_validate(booking)
    detail.service_name = booking.service.name if booking.service else None
    detail.staff_name = booking.staff.name if booking.staff else None
    return detail


@router.post("", response_model=BookingRead)
def create_patient_booking(data: BookingCreate, db: DbSession, request: Request) -> Booking:
    booking = create_booking(db, data)
    write_audit_log(db, action="booking.create", entity_type="Booking", entity_id=booking.id, request=request, new_value=model_snapshot(booking))
    db.commit()
    send_booking_alerts(booking, db)
    db.commit()
    return booking


@router.get("", response_model=None, dependencies=[Depends(require_permission("bookings.read"))])
def list_bookings(
    db: DbSession,
    status: BookingStatus | None = Query(default=None),
    booking_date: date | None = Query(default=None),
    page: int | None = Query(default=None),
    limit: int | None = Query(default=None),
):
    query = select(Booking).options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    if status:
        query = query.where(Booking.status == status)
    if booking_date:
        query = query.where(Booking.booking_date == booking_date)
    query = query.order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
    if page is not None and limit is not None:
        result = paginate_query(db, query, page, limit)
        result["items"] = [to_booking_detail(booking) for booking in result["items"]]
        return result
    bookings = db.scalars(query).unique().all()
    return [to_booking_detail(booking) for booking in bookings]


@router.get("/slots")
def get_available_slots(
    db: DbSession,
    service_id: int = Query(...),
    selected_date: date = Query(...),
    staff_id: int | None = Query(default=None),
) -> dict:
    return {"slots": available_slots(db, service_id, selected_date, staff_id)}


@router.get("/slots/week")
def get_slots_week(
    db: DbSession,
    service_id: int = Query(...),
    start_date: date = Query(...),
    days: int = Query(default=30, ge=1, le=31),
    staff_id: int | None = Query(default=None),
) -> dict:
    """Return {date: {free, taken}} for up to 31 days — 3 DB queries total."""
    return available_slots_range(db, service_id, start_date, days, staff_id)


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


@router.get("/me", response_model=list[BookingDetail])
def my_bookings(db: DbSession, user=Depends(get_current_user)) -> list[BookingDetail]:
    bookings = db.scalars(
        select(Booking)
        .join(Booking.patient)
        .where(Booking.patient.has(email=user.email))
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
        .order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
    ).unique().all()
    return [to_booking_detail(booking) for booking in bookings]


@router.get("/calendar", response_model=list[BookingDetail], dependencies=[Depends(require_permission("bookings.read"))])
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


@router.get("/{booking_id}", response_model=BookingDetail, dependencies=[Depends(require_permission("bookings.read"))])
def get_booking(booking_id: int, db: DbSession) -> BookingDetail:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return to_booking_detail(booking)


@router.patch("/{booking_id}", response_model=BookingRead, dependencies=[Depends(require_permission("bookings.manage"))])
def patch_booking(booking_id: int, data: BookingUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    old_value = model_snapshot(booking)
    booking = update_booking(db, booking, data)
    write_audit_log(db, action="booking.update", entity_type="Booking", entity_id=booking.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(booking))
    db.commit()
    return booking


@router.patch("/{booking_id}/status", response_model=BookingRead, dependencies=[Depends(require_permission("bookings.manage"))])
def update_booking_status(booking_id: int, data: BookingStatusUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Booking:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.patient), joinedload(Booking.service), joinedload(Booking.staff))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    old_value = model_snapshot(booking)
    set_booking_status(db, booking, data.status, data.notes)
    template = template_for_status(data.status)
    if template:
        mail = create_booking_mail(booking, template, db=db)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(booking)
    action = f"booking.{data.status}"
    write_audit_log(db, action=action, entity_type="Booking", entity_id=booking.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(booking))
    db.commit()
    return booking


@router.post("/{booking_id}/mail/{template}", dependencies=[Depends(require_permission("mail.manage"))])
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
    mail = create_booking_mail(booking, template, MailStatus.queued, db=db)
    if not mail:
        raise HTTPException(status_code=400, detail="Patient email is missing")
    db.add(mail)
    db.commit()
    return {"message": "Mail queued", "template": template}
