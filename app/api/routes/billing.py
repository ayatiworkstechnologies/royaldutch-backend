from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_admin
from app.models.billing import Invoice, InvoiceItem
from app.models.booking import Booking
from app.models.enums import MailStatus
from app.models.enums import InvoiceStatus
from app.schemas.billing import InvoiceCreate, InvoiceFromBookingCreate, InvoiceRead, InvoiceUpdate
from app.services.invoice_pdf_service import generate_invoice_pdf, invoice_pdf_filename
from app.services.mail_service import create_invoice_mail
from app.services.settings_service import get_clinic_settings
from app.services.smtp_service import send_mail_message

router = APIRouter(prefix="/billing", tags=["billing"], dependencies=[Depends(get_current_admin)])


def invoice_number() -> str:
    return f"INV-{date.today():%y%m%d}-{uuid4().hex[:5].upper()}"


def apply_items(invoice: Invoice, items_data) -> None:
    invoice.items = [
        InvoiceItem(
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            line_total=item.unit_price * item.quantity,
        )
        for item in items_data
    ]


def recalculate(invoice: Invoice) -> None:
    subtotal = sum((item.line_total for item in invoice.items), Decimal("0"))
    invoice.subtotal = subtotal
    invoice.total_amount = subtotal - invoice.discount_amount + invoice.tax_amount
    invoice.balance_due = invoice.total_amount - invoice.paid_amount
    if invoice.balance_due <= 0 and invoice.total_amount > 0:
        invoice.status = InvoiceStatus.paid
    elif invoice.paid_amount > 0 and invoice.balance_due > 0:
        invoice.status = InvoiceStatus.partially_paid


def invoice_detail_query():
    return select(Invoice).options(
        joinedload(Invoice.items),
        joinedload(Invoice.patient),
        joinedload(Invoice.booking).joinedload(Booking.patient),
        joinedload(Invoice.booking).joinedload(Booking.service),
    )


@router.get("", response_model=list[InvoiceRead])
def list_invoices(db: DbSession) -> list[Invoice]:
    return list(db.scalars(invoice_detail_query().order_by(Invoice.created_at.desc())).unique().all())


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: DbSession) -> Invoice:
    invoice = db.scalar(invoice_detail_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("", response_model=InvoiceRead)
def create_invoice(data: InvoiceCreate, db: DbSession) -> Invoice:
    invoice = Invoice(**data.model_dump(exclude={"items"}), invoice_number=invoice_number())
    apply_items(invoice, data.items)
    recalculate(invoice)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/from-booking/{booking_id}", response_model=InvoiceRead)
def create_invoice_from_booking(booking_id: int, data: InvoiceFromBookingCreate, db: DbSession) -> Invoice:
    booking = db.scalar(
        select(Booking)
        .where(Booking.id == booking_id)
        .options(joinedload(Booking.service), joinedload(Booking.patient))
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    existing = db.scalar(select(Invoice).where(Invoice.booking_id == booking.id).options(joinedload(Invoice.items)))
    if existing:
        return existing

    unit_price = booking.price or Decimal("0")
    invoice = Invoice(
        invoice_number=invoice_number(),
        booking_id=booking.id,
        patient_id=booking.patient_id,
        issue_date=date.today(),
        due_date=data.due_date,
        discount_amount=data.discount_amount,
        tax_amount=data.tax_amount,
        paid_amount=Decimal("0"),
        currency=booking.currency,
        status=InvoiceStatus.issued,
        notes=data.notes,
    )
    invoice.items = [
        InvoiceItem(
            description=booking.service.name if booking.service else "Clinic service",
            quantity=1,
            unit_price=unit_price,
            line_total=unit_price,
        )
    ]
    recalculate(invoice)
    if invoice.status == InvoiceStatus.draft:
        invoice.status = InvoiceStatus.issued
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: DbSession) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).options(joinedload(Invoice.items)))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    update_data = data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in update_data.items():
        setattr(invoice, field, value)
    if data.items is not None:
        apply_items(invoice, data.items)
    recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: int, db: DbSession) -> dict:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted"}


@router.post("/{invoice_id}/mail/{template}")
def queue_invoice_mail(invoice_id: int, template: str, db: DbSession) -> dict:
    allowed_templates = {"invoice_issued"}
    if template not in allowed_templates:
        raise HTTPException(status_code=400, detail="Unknown invoice mail template")
    invoice = db.scalar(invoice_detail_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    mail = create_invoice_mail(invoice, template, MailStatus.queued, db=db)
    if not mail:
        raise HTTPException(status_code=400, detail="Patient email is missing")
    db.add(mail)
    db.commit()
    return {"message": "Invoice mail queued", "template": template}


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(invoice_id: int, db: DbSession) -> Response:
    invoice = db.scalar(invoice_detail_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    pdf = generate_invoice_pdf(invoice, get_clinic_settings(db))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice_pdf_filename(invoice)}"'},
    )


@router.post("/{invoice_id}/send")
def send_invoice_email(invoice_id: int, db: DbSession, attach_pdf: bool = True) -> dict:
    invoice = db.scalar(invoice_detail_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    mail = create_invoice_mail(invoice, "invoice_issued", MailStatus.queued, db=db)
    if not mail:
        raise HTTPException(status_code=400, detail="Patient email is missing")

    attachments = []
    if attach_pdf:
        attachments.append(
            (
                invoice_pdf_filename(invoice),
                generate_invoice_pdf(invoice, get_clinic_settings(db)),
                "application/pdf",
            )
        )
    send_mail_message(mail, attachments=attachments)
    db.add(mail)
    db.commit()
    return {"message": "Invoice email processed", "status": mail.status, "error_message": mail.error_message}
