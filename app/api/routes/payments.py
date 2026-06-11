from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.api.routes.billing import recalculate
from app.models.billing import Invoice
from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(get_current_admin)])

COUNTED_PAYMENT_STATUSES = {PaymentStatus.paid, PaymentStatus.partially_paid}


def get_invoice_or_404(db: DbSession, invoice_id: int | None) -> Invoice | None:
    if not invoice_id:
        return None
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def sync_invoice_paid_amount(db: DbSession, invoice_id: int | None) -> None:
    if not invoice_id:
        return
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id))
    if not invoice:
        return
    payments = db.scalars(
        select(Payment).where(
            Payment.invoice_id == invoice_id,
            Payment.payment_status.in_(COUNTED_PAYMENT_STATUSES),
        )
    ).all()
    invoice.paid_amount = sum((payment.amount for payment in payments), start=Decimal("0"))
    recalculate(invoice)


@router.get("", response_model=list[PaymentRead])
def list_payments(db: DbSession) -> list[Payment]:
    return list(db.scalars(select(Payment).order_by(Payment.created_at.desc())).all())


@router.post("", response_model=PaymentRead)
def create_payment(data: PaymentCreate, db: DbSession) -> Payment:
    get_invoice_or_404(db, data.invoice_id)
    payment = Payment(**data.model_dump())
    db.add(payment)
    db.flush()
    sync_invoice_paid_amount(db, payment.invoice_id)
    db.commit()
    db.refresh(payment)
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id: int, data: PaymentUpdate, db: DbSession) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    old_invoice_id = payment.invoice_id
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    get_invoice_or_404(db, payment.invoice_id)
    db.flush()
    sync_invoice_paid_amount(db, old_invoice_id)
    if payment.invoice_id != old_invoice_id:
        sync_invoice_paid_amount(db, payment.invoice_id)
    db.commit()
    db.refresh(payment)
    return payment
