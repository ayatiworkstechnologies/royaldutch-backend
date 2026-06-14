from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceItem
from app.models.booking import Booking
from app.models.enums import InvoiceStatus
from app.schemas.billing import InvoiceCreate, InvoiceFromBookingCreate, InvoiceUpdate


def invoice_number() -> str:
    return f"INV-{date.today():%y%m%d}-{uuid4().hex[:5].upper()}"


def is_unique_invoice_number_error(exc: IntegrityError) -> bool:
    text = str(exc.orig).lower()
    return "invoice_number" in text or "invoices.invoice_number" in text


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


def recalculate_invoice(invoice: Invoice) -> None:
    subtotal = sum((item.line_total for item in invoice.items), Decimal("0"))
    invoice.subtotal = subtotal
    invoice.total_amount = subtotal - invoice.discount_amount + invoice.tax_amount
    invoice.balance_due = invoice.total_amount - invoice.paid_amount
    if invoice.balance_due <= 0 and invoice.total_amount > 0:
        invoice.status = InvoiceStatus.paid
    elif invoice.paid_amount > 0 and invoice.balance_due > 0:
        invoice.status = InvoiceStatus.partially_paid


def create_invoice_with_retry(db: Session, data: InvoiceCreate) -> Invoice:
    for _ in range(3):
        invoice = Invoice(**data.model_dump(exclude={"items"}), invoice_number=invoice_number())
        apply_items(invoice, data.items)
        recalculate_invoice(invoice)
        db.add(invoice)
        try:
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError as exc:
            db.rollback()
            if not is_unique_invoice_number_error(exc):
                raise
    raise HTTPException(status_code=409, detail="Could not allocate invoice number. Please retry.")


def create_invoice_from_booking_with_retry(db: Session, booking: Booking, data: InvoiceFromBookingCreate) -> Invoice:
    unit_price = booking.price or Decimal("0")
    for _ in range(3):
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
        recalculate_invoice(invoice)
        if invoice.status == InvoiceStatus.draft:
            invoice.status = InvoiceStatus.issued
        db.add(invoice)
        try:
            db.commit()
            db.refresh(invoice)
            return invoice
        except IntegrityError as exc:
            db.rollback()
            if not is_unique_invoice_number_error(exc):
                raise
    raise HTTPException(status_code=409, detail="Could not allocate invoice number. Please retry.")


def update_invoice_values(db: Session, invoice: Invoice, data: InvoiceUpdate) -> Invoice:
    update_data = data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in update_data.items():
        setattr(invoice, field, value)
    if data.items is not None:
        apply_items(invoice, data.items)
    recalculate_invoice(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
