from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.models.billing import Invoice
from app.models.booking import Booking
from app.models.patient import Patient
from app.models.user import User
from app.schemas.billing import InvoiceRead
from app.schemas.patient import PatientUpdate
from app.services.invoice_pdf_service import generate_invoice_pdf, invoice_pdf_filename
from app.services.settings_service import get_clinic_settings

router = APIRouter(prefix="/account", tags=["customer account"])


def customer_patient_query(user: User):
    return select(Patient).where((Patient.user_id == user.id) | (Patient.email == user.email))


def get_customer_patient(db: DbSession, user: User) -> Patient:
    patient = db.scalar(customer_patient_query(user).order_by(Patient.updated_at.desc()))
    if not patient:
        raise HTTPException(status_code=404, detail="Patient profile not found")
    if not patient.user_id:
        patient.user_id = user.id
        db.commit()
        db.refresh(patient)
    return patient


def optional_customer_patient(db: DbSession, user: User) -> Patient | None:
    return db.scalar(customer_patient_query(user).order_by(Patient.updated_at.desc()))


def profile_payload(user: User, patient: Patient | None) -> dict:
    return {
        "id": patient.id if patient else None,
        "full_name": patient.full_name if patient else user.name,
        "email": user.email,
        "phone": patient.phone if patient else "",
        "gender": patient.gender if patient else "",
        "age": patient.age if patient else None,
        "notes": patient.notes if patient else "",
        "documents": patient.documents if patient else "",
    }


def customer_invoice_query(user: User):
    return (
        select(Invoice)
        .join(Patient, (Invoice.patient_id == Patient.id) | (Invoice.booking.has(Booking.patient_id == Patient.id)))
        .where((Patient.user_id == user.id) | (Patient.email == user.email))
        .options(
            joinedload(Invoice.items),
            joinedload(Invoice.patient),
            joinedload(Invoice.booking).joinedload(Booking.patient),
            joinedload(Invoice.booking).joinedload(Booking.service),
        )
    )


@router.get("/me")
def my_profile(db: DbSession, user: User = Depends(get_current_user)) -> dict:
    patient = optional_customer_patient(db, user)
    if patient and not patient.user_id:
        patient.user_id = user.id
        db.commit()
        db.refresh(patient)
    return profile_payload(user, patient)


@router.patch("/me")
def update_my_profile(data: PatientUpdate, db: DbSession, user: User = Depends(get_current_user)) -> dict:
    patient = optional_customer_patient(db, user)
    values = data.model_dump(exclude_unset=True)
    if "email" in values and values["email"] and values["email"].lower().strip() != user.email:
        raise HTTPException(status_code=400, detail="Email cannot be changed from the customer portal")
    phone = values.get("phone")
    full_name = values.get("full_name")
    if not patient and (not phone or not full_name):
        raise HTTPException(status_code=400, detail="Full name and phone are required")
    if phone and (not patient or phone != patient.phone):
        existing_query = select(Patient).where(Patient.phone == values["phone"])
        if patient:
            existing_query = existing_query.where(Patient.id != patient.id)
        existing = db.scalar(existing_query)
        if existing:
            raise HTTPException(status_code=400, detail="Patient with this phone number already exists")
    if not patient:
        patient = Patient(full_name=full_name, phone=phone, email=user.email, user_id=user.id)
        db.add(patient)
        db.flush()
    for field, value in values.items():
        if field == "email" and value:
            value = value.lower().strip()
        setattr(patient, field, value)
    patient.email = user.email
    patient.user_id = user.id
    db.commit()
    db.refresh(patient)
    return profile_payload(user, patient)


@router.get("/invoices", response_model=list[InvoiceRead])
def my_invoices(db: DbSession, user: User = Depends(get_current_user)) -> list[Invoice]:
    return list(db.scalars(customer_invoice_query(user).order_by(Invoice.created_at.desc())).unique().all())


@router.get("/invoices/{invoice_id}/pdf")
def my_invoice_pdf(invoice_id: int, db: DbSession, user: User = Depends(get_current_user)) -> Response:
    invoice = db.scalar(customer_invoice_query(user).where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    pdf = generate_invoice_pdf(invoice, get_clinic_settings(db))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice_pdf_filename(invoice)}"'},
    )
