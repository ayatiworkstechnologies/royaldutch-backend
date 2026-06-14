from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.patient_document import PatientDocument
from app.models.user import User
from app.schemas.patient_document import PatientDocumentCreate, PatientDocumentUpdate


def ensure_patient(db: Session, patient_id: int) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def create_patient_document(db: Session, patient_id: int, data: PatientDocumentCreate, user: User | None = None) -> PatientDocument:
    ensure_patient(db, patient_id)
    document = PatientDocument(
        patient_id=patient_id,
        title=data.title,
        document_type=data.document_type,
        file_name=data.file_name,
        content_type=data.content_type,
        storage_key=f"patients/{patient_id}/{uuid4().hex}-{data.file_name}",
        external_url=data.external_url,
        notes=data.notes,
        uploaded_by_user_id=user.id if user else None,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_patient_documents(db: Session, patient_id: int, document_type: str | None = None) -> list[PatientDocument]:
    ensure_patient(db, patient_id)
    query = select(PatientDocument).where(PatientDocument.patient_id == patient_id).order_by(PatientDocument.created_at.desc())
    if document_type:
        query = query.where(PatientDocument.document_type == document_type)
    return list(db.scalars(query).all())


def update_patient_document(db: Session, document: PatientDocument, data: PatientDocumentUpdate) -> PatientDocument:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(document, field, value)
    db.commit()
    db.refresh(document)
    return document
