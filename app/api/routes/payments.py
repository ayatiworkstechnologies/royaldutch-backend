from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.api.routes.billing import recalculate
from app.models.billing import Invoice
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[PaymentRead])
def list_payments(db: DbSession) -> list[Payment]:
    return list(db.scalars(select(Payment).order_by(Payment.created_at.desc())).all())


@router.post("", response_model=PaymentRead)
def create_payment(data: PaymentCreate, db: DbSession) -> Payment:
    payment = Payment(**data.model_dump())
    db.add(payment)
    if payment.invoice_id and payment.payment_status in {"paid", "partially_paid"}:
        invoice = db.scalar(select(Invoice).where(Invoice.id == payment.invoice_id))
        if invoice:
            invoice.paid_amount += payment.amount
            recalculate(invoice)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id: int, data: PaymentUpdate, db: DbSession) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    old_invoice_id = payment.invoice_id
    old_amount = payment.amount
    old_status = payment.payment_status
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    if old_invoice_id and old_status in {"paid", "partially_paid"}:
        invoice = db.scalar(select(Invoice).where(Invoice.id == old_invoice_id))
        if invoice:
            invoice.paid_amount -= old_amount
            recalculate(invoice)
    if payment.invoice_id and payment.payment_status in {"paid", "partially_paid"}:
        invoice = db.scalar(select(Invoice).where(Invoice.id == payment.invoice_id))
        if invoice:
            invoice.paid_amount += payment.amount
            recalculate(invoice)
    db.commit()
    db.refresh(payment)
    return payment
