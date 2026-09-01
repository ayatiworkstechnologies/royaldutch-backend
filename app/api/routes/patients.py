from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.patient import Patient
from app.models.user import User
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.schemas.patient_detail import PatientDetail
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.patient_service import get_patient_detail
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=None, dependencies=[Depends(require_permission("patients.read"))])
def list_patients(
    db: DbSession,
    phone: str | None = Query(default=None),
    page: int | None = Query(default=None),
    limit: int | None = Query(default=None),
):
    query = select(Patient).order_by(Patient.full_name)
    if phone:
        query = query.where(Patient.phone == phone)
    if page is not None and limit is not None:
        return paginate_query(db, query, page, limit)
    return list(db.scalars(query).all())


@router.get("/{patient_id}", response_model=PatientDetail, dependencies=[Depends(require_permission("patients.read"))])
def get_patient(patient_id: int, db: DbSession) -> Patient:
    return get_patient_detail(db, patient_id)


@router.post("", response_model=PatientRead, dependencies=[Depends(require_permission("patients.manage"))])
def create_patient(data: PatientCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Patient:
    existing = db.scalar(select(Patient).where(Patient.phone == data.phone))
    if existing:
        raise HTTPException(status_code=400, detail="Patient with this phone number already exists")
    patient = Patient(**data.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    write_audit_log(db, action="patient.create", entity_type="Patient", entity_id=patient.id, user=user, request=request, new_value=model_snapshot(patient))
    db.commit()
    return patient


@router.patch("/{patient_id}", response_model=PatientRead, dependencies=[Depends(require_permission("patients.manage"))])
def update_patient(patient_id: int, data: PatientUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    old_value = model_snapshot(patient)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    write_audit_log(db, action="patient.update", entity_type="Patient", entity_id=patient.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(patient))
    db.commit()
    return patient


@router.delete("/{patient_id}", dependencies=[Depends(require_permission("patients.manage"))])
def delete_patient(patient_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    old_value = model_snapshot(patient)
    db.delete(patient)
    write_audit_log(db, action="patient.delete", entity_type="Patient", entity_id=patient_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Patient deleted"}
