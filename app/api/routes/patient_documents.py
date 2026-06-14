from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.patient_document import PatientDocument
from app.models.user import User
from app.schemas.patient_document import PatientDocumentCreate, PatientDocumentRead, PatientDocumentUpdate
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.patient_document_service import create_patient_document, list_patient_documents, update_patient_document

router = APIRouter(prefix="/patients/{patient_id}/documents", tags=["patient documents"])


@router.get("", response_model=list[PatientDocumentRead], dependencies=[Depends(require_permission("patients.read"))])
def list_documents(patient_id: int, db: DbSession, document_type: str | None = Query(default=None)) -> list[PatientDocument]:
    return list_patient_documents(db, patient_id, document_type)


@router.post("", response_model=PatientDocumentRead, dependencies=[Depends(require_permission("patients.manage"))])
def create_document(patient_id: int, data: PatientDocumentCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> PatientDocument:
    document = create_patient_document(db, patient_id, data, user)
    write_audit_log(db, action="patient_document.create", entity_type="PatientDocument", entity_id=document.id, user=user, request=request, new_value=model_snapshot(document))
    db.commit()
    return document


@router.patch("/{document_id}", response_model=PatientDocumentRead, dependencies=[Depends(require_permission("patients.manage"))])
def patch_document(patient_id: int, document_id: int, data: PatientDocumentUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> PatientDocument:
    document = db.get(PatientDocument, document_id)
    if not document or document.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Patient document not found")
    old_value = model_snapshot(document)
    document = update_patient_document(db, document, data)
    write_audit_log(db, action="patient_document.update", entity_type="PatientDocument", entity_id=document.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(document))
    db.commit()
    return document


@router.delete("/{document_id}", dependencies=[Depends(require_permission("patients.manage"))])
def delete_document(patient_id: int, document_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    document = db.get(PatientDocument, document_id)
    if not document or document.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="Patient document not found")
    old_value = model_snapshot(document)
    db.delete(document)
    write_audit_log(db, action="patient_document.delete", entity_type="PatientDocument", entity_id=document_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Patient document deleted"}
