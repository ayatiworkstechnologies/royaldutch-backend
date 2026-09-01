from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.patient import Patient
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionUpdate


def ensure_booking(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


def ensure_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def create_prescription(db: Session, booking: Booking, data: PrescriptionCreate, user: User | None = None) -> Prescription:
    prescription = Prescription(
        patient_id=booking.patient_id,
        booking_id=booking.id,
        staff_id=user.staff_id if user else None,
        drug_name=data.drug_name,
        dosage=data.dosage,
        frequency=data.frequency,
        duration=data.duration,
        notes=data.notes,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


def list_prescriptions_for_patient(db: Session, patient_id: int) -> list[Prescription]:
    ensure_patient(db, patient_id)
    query = select(Prescription).where(Prescription.patient_id == patient_id).order_by(Prescription.created_at.desc())
    return list(db.scalars(query).all())


def list_prescriptions_for_booking(db: Session, booking_id: int) -> list[Prescription]:
    query = select(Prescription).where(Prescription.booking_id == booking_id).order_by(Prescription.created_at.desc())
    return list(db.scalars(query).all())


def update_prescription(db: Session, prescription: Prescription, data: PrescriptionUpdate) -> Prescription:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(prescription, field, value)
    db.commit()
    db.refresh(prescription)
    return prescription
