from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[PatientRead])
def list_patients(db: DbSession, phone: str | None = Query(default=None)) -> list[Patient]:
    query = select(Patient).order_by(Patient.full_name)
    if phone:
        query = query.where(Patient.phone == phone)
    return list(db.scalars(query).all())


@router.post("", response_model=PatientRead)
def create_patient(data: PatientCreate, db: DbSession) -> Patient:
    existing = db.scalar(select(Patient).where(Patient.phone == data.phone))
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone number already exists")
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, data: PatientUpdate, db: DbSession) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient
