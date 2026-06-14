from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.billing import Invoice
from app.models.booking import Booking
from app.models.enums import MailStatus
from app.models.user import User
from app.schemas.billing import InvoiceCreate, InvoiceFromBookingCreate, InvoiceRead, InvoiceUpdate
from app.services.billing_service import create_invoice_from_booking_with_retry, create_invoice_with_retry, update_invoice_values
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.invoice_pdf_service import generate_invoice_pdf, invoice_pdf_filename
from app.services.mail_service import create_invoice_mail
from app.services.settings_service import get_clinic_settings
from app.services.smtp_service import send_mail_message
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/billing", tags=["billing"], dependencies=[Depends(require_permission("billing.manage"))])


def invoice_detail_query():
    return select(Invoice).options(
        joinedload(Invoice.items),
        joinedload(Invoice.patient),
        joinedload(Invoice.booking).joinedload(Booking.patient),
        joinedload(Invoice.booking).joinedload(Booking.service),
    )


@router.get("", response_model=None)
def list_invoices(db: DbSession, page: int | None = Query(default=None), limit: int | None = Query(default=None)):
    query = invoice_detail_query().order_by(Invoice.created_at.desc())
    if page is not None and limit is not None:
        result = paginate_query(db, query, page, limit)
        result["items"] = [InvoiceRead.model_validate(item).model_dump(mode="json") for item in result["items"]]
        return result
    return [InvoiceRead.model_validate(item).model_dump(mode="json") for item in db.scalars(query).unique().all()]


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: DbSession) -> Invoice:
    invoice = db.scalar(invoice_detail_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("", response_model=InvoiceRead)
def create_invoice(data: InvoiceCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Invoice:
    invoice = create_invoice_with_retry(db, data)
    write_audit_log(db, action="invoice.create", entity_type="Invoice", entity_id=invoice.id, user=user, request=request, new_value=model_snapshot(invoice))
    db.commit()
    return invoice


@router.post("/from-booking/{booking_id}", response_model=InvoiceRead)
def create_invoice_from_booking(booking_id: int, data: InvoiceFromBookingCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Invoice:
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

    invoice = create_invoice_from_booking_with_retry(db, booking, data)
    write_audit_log(db, action="invoice.create", entity_type="Invoice", entity_id=invoice.id, user=user, request=request, new_value=model_snapshot(invoice))
    db.commit()
    return invoice


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, data: InvoiceUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Invoice:
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).options(joinedload(Invoice.items)))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    old_value = model_snapshot(invoice)

    invoice = update_invoice_values(db, invoice, data)
    write_audit_log(db, action="invoice.update", entity_type="Invoice", entity_id=invoice.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(invoice))
    db.commit()
    return invoice


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    old_value = model_snapshot(invoice)
    db.delete(invoice)
    write_audit_log(db, action="invoice.delete", entity_type="Invoice", entity_id=invoice_id, user=user, request=request, old_value=old_value)
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
def send_invoice_email(invoice_id: int, db: DbSession, request: Request, attach_pdf: bool = True, user: User = Depends(get_current_user)) -> dict:
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
    write_audit_log(db, action="invoice.send", entity_type="Invoice", entity_id=invoice.id, user=user, request=request, new_value={"mail_status": mail.status, "attach_pdf": attach_pdf})
    db.commit()
    return {"message": "Invoice email processed", "status": mail.status, "error_message": mail.error_message}
