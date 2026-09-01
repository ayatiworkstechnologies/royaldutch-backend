from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.models.booking import Booking
from app.models.enums import BookingStatus
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.staff import Staff
from app.models.user import User
from app.schemas.booking import BookingDetail, BookingStatusUpdate, BookingRead
from app.schemas.patient import PatientRead
from app.schemas.patient_detail import PatientDetail
from app.schemas.prescription import PrescriptionCreate, PrescriptionRead
from app.services.booking_service import update_booking_status as set_booking_status
from app.services.mail_service import create_booking_mail, template_for_status
from app.services.patient_service import ensure_staff_treats_patient, get_patient_detail, list_patients_for_staff
from app.services.prescription_service import create_prescription, list_prescriptions_for_booking

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
    set_booking_status(db, booking, data.status, data.reason, data.notes)
    template = template_for_status(data.status)
    if template:
        mail = create_booking_mail(booking, template, db=db)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(booking)
    return booking


def _my_booking(db: DbSession, booking_id: int, user: User) -> Booking:
    if not user.staff_id:
        raise HTTPException(status_code=403, detail="No staff profile linked to this account")
    booking = db.scalar(select(Booking).where(Booking.id == booking_id, Booking.staff_id == user.staff_id))
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.get("/bookings/{booking_id}/prescriptions", response_model=list[PrescriptionRead])
def my_booking_prescriptions(
    booking_id: int,
    db: DbSession,
    user: User = Depends(_require_clinical),
) -> list[Prescription]:
    _my_booking(db, booking_id, user)
    return list_prescriptions_for_booking(db, booking_id)


@router.post("/bookings/{booking_id}/prescriptions", response_model=PrescriptionRead)
def add_my_booking_prescription(
    booking_id: int,
    data: PrescriptionCreate,
    db: DbSession,
    user: User = Depends(_require_clinical),
) -> Prescription:
    booking = _my_booking(db, booking_id, user)
    return create_prescription(db, booking, data, user)


@router.get("/patients", response_model=list[PatientRead])
def my_patients(db: DbSession, user: User = Depends(_require_clinical)) -> list[Patient]:
    if not user.staff_id:
        return []
    return list_patients_for_staff(db, user.staff_id)


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def my_patient_detail(patient_id: int, db: DbSession, user: User = Depends(_require_clinical)) -> Patient:
    if not user.staff_id:
        raise HTTPException(status_code=403, detail="No staff profile linked to this account")
    ensure_staff_treats_patient(db, user.staff_id, patient_id)
    return get_patient_detail(db, patient_id)
