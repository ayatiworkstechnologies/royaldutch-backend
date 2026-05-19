from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_admin
from app.models.billing import Invoice, InvoiceItem
from app.models.booking import Booking
from app.models.enums import InvoiceStatus
from app.schemas.billing import InvoiceCreate, InvoiceFromBookingCreate, InvoiceRead, InvoiceUpdate

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


@router.get("", response_model=list[InvoiceRead])
def list_invoices(db: DbSession) -> list[Invoice]:
    return list(db.scalars(select(Invoice).options(joinedload(Invoice.items)).order_by(Invoice.created_at.desc())).unique().all())


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
