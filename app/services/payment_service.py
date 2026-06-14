from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice
from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.services.billing_service import recalculate_invoice

COUNTED_PAYMENT_STATUSES = {PaymentStatus.paid, PaymentStatus.partially_paid}


def sync_invoice_paid_amount(db: Session, invoice_id: int | None) -> None:
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
    invoice.paid_amount = sum((payment.amount - payment.refund_amount for payment in payments), start=Decimal("0"))
    recalculate_invoice(invoice)
