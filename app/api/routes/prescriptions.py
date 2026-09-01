from fastapi import APIRouter, Depends, HTTPException, Request

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.prescription import Prescription
from app.models.user import User
from app.schemas.prescription import PrescriptionCreate, PrescriptionRead, PrescriptionUpdate
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.prescription_service import (
    create_prescription,
    ensure_booking,
    list_prescriptions_for_booking,
    list_prescriptions_for_patient,
    update_prescription,
)

router = APIRouter(tags=["prescriptions"])


@router.get(
    "/patients/{patient_id}/prescriptions",
    response_model=list[PrescriptionRead],
    dependencies=[Depends(require_permission("prescriptions.read"))],
)
def list_patient_prescriptions(patient_id: int, db: DbSession) -> list[Prescription]:
    return list_prescriptions_for_patient(db, patient_id)


@router.get(
    "/bookings/{booking_id}/prescriptions",
    response_model=list[PrescriptionRead],
    dependencies=[Depends(require_permission("prescriptions.read"))],
)
def list_booking_prescriptions(booking_id: int, db: DbSession) -> list[Prescription]:
    ensure_booking(db, booking_id)
    return list_prescriptions_for_booking(db, booking_id)


@router.post(
    "/bookings/{booking_id}/prescriptions",
    response_model=PrescriptionRead,
    dependencies=[Depends(require_permission("prescriptions.manage"))],
)
def add_booking_prescription(
    booking_id: int,
    data: PrescriptionCreate,
    db: DbSession,
    request: Request,
    user: User = Depends(get_current_user),
) -> Prescription:
    booking = ensure_booking(db, booking_id)
    prescription = create_prescription(db, booking, data, user)
    write_audit_log(
        db,
        action="prescription.create",
        entity_type="Prescription",
        entity_id=prescription.id,
        user=user,
        request=request,
        new_value=model_snapshot(prescription),
    )
    db.commit()
    return prescription


@router.patch(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionRead,
    dependencies=[Depends(require_permission("prescriptions.manage"))],
)
def patch_prescription(
    prescription_id: int,
    data: PrescriptionUpdate,
    db: DbSession,
    request: Request,
    user: User = Depends(get_current_user),
) -> Prescription:
    prescription = db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    old_value = model_snapshot(prescription)
    prescription = update_prescription(db, prescription, data)
    write_audit_log(
        db,
        action="prescription.update",
        entity_type="Prescription",
        entity_id=prescription.id,
        user=user,
        request=request,
        old_value=old_value,
        new_value=model_snapshot(prescription),
    )
    db.commit()
    return prescription


@router.delete(
    "/prescriptions/{prescription_id}",
    dependencies=[Depends(require_permission("prescriptions.manage"))],
)
def delete_prescription(
    prescription_id: int,
    db: DbSession,
    request: Request,
    user: User = Depends(get_current_user),
) -> dict:
    prescription = db.get(Prescription, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    old_value = model_snapshot(prescription)
    db.delete(prescription)
    write_audit_log(
        db,
        action="prescription.delete",
        entity_type="Prescription",
        entity_id=prescription_id,
        user=user,
        request=request,
        old_value=old_value,
    )
    db.commit()
    return {"message": "Prescription deleted"}
