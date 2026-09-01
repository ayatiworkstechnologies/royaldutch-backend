from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.booking import Booking
from app.models.patient import Patient


def get_patient_or_404(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def get_patient_detail(db: Session, patient_id: int) -> Patient:
    patient = db.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .options(
            joinedload(Patient.bookings).joinedload(Booking.service),
            joinedload(Patient.bookings).joinedload(Booking.staff),
            joinedload(Patient.prescriptions),
            joinedload(Patient.patient_documents),
        )
    ).unique().scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    patient.bookings.sort(key=lambda b: (b.booking_date, b.booking_time), reverse=True)
    return patient


def list_patients_for_staff(db: Session, staff_id: int) -> list[Patient]:
    query = (
        select(Patient)
        .join(Booking, Booking.patient_id == Patient.id)
        .where(Booking.staff_id == staff_id)
        .distinct()
        .order_by(Patient.full_name)
    )
    return list(db.scalars(query).unique().all())


def ensure_staff_treats_patient(db: Session, staff_id: int, patient_id: int) -> None:
    booking = db.scalar(
        select(Booking).where(Booking.staff_id == staff_id, Booking.patient_id == patient_id)
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Patient not found")
