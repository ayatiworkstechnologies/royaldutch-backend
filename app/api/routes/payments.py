from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.billing import Invoice
from app.models.booking import Booking
from app.models.enums import MailStatus, PaymentStatus
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate
from app.services.mail_service import create_payment_mail
from app.services.payment_service import COUNTED_PAYMENT_STATUSES, sync_invoice_paid_amount
from app.services.audit_service import model_snapshot, write_audit_log
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/payments", tags=["payments"], dependencies=[Depends(require_permission("payments.manage"))])

def get_invoice_or_404(db: DbSession, invoice_id: int | None) -> Invoice | None:
    if not invoice_id:
        return None
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

def payment_detail_query():
    return select(Payment).options(
        joinedload(Payment.invoice).joinedload(Invoice.patient),
        joinedload(Payment.invoice).joinedload(Invoice.booking).joinedload(Booking.patient),
        joinedload(Payment.invoice).joinedload(Invoice.booking).joinedload(Booking.service),
    )


@router.get("", response_model=None)
def list_payments(db: DbSession, page: int | None = Query(default=None), limit: int | None = Query(default=None)):
    query = select(Payment).order_by(Payment.created_at.desc())
    if page is not None and limit is not None:
        result = paginate_query(db, query, page, limit)
        result["items"] = [PaymentRead.model_validate(item).model_dump(mode="json") for item in result["items"]]
        return result
    return [PaymentRead.model_validate(item).model_dump(mode="json") for item in db.scalars(query).all()]


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(payment_id: int, db: DbSession) -> Payment:
    payment = db.scalar(payment_detail_query().where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("", response_model=PaymentRead)
def create_payment(data: PaymentCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Payment:
    get_invoice_or_404(db, data.invoice_id)
    payment = Payment(**data.model_dump())
    db.add(payment)
    db.flush()
    sync_invoice_paid_amount(db, payment.invoice_id)
    if payment.payment_status in COUNTED_PAYMENT_STATUSES:
        mail = create_payment_mail(payment, "payment_received", MailStatus.queued, db=db)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(payment)
    write_audit_log(db, action="payment.create", entity_type="Payment", entity_id=payment.id, user=user, request=request, new_value=model_snapshot(payment))
    db.commit()
    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id: int, data: PaymentUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Payment:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    old_value = model_snapshot(payment)
    old_invoice_id = payment.invoice_id
    old_status = payment.payment_status
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    get_invoice_or_404(db, payment.invoice_id)
    db.flush()
    sync_invoice_paid_amount(db, old_invoice_id)
    if payment.invoice_id != old_invoice_id:
        sync_invoice_paid_amount(db, payment.invoice_id)
    if payment.payment_status in COUNTED_PAYMENT_STATUSES and old_status not in COUNTED_PAYMENT_STATUSES:
        mail = create_payment_mail(payment, "payment_received", MailStatus.queued, db=db)
        if mail:
            db.add(mail)
    db.commit()
    db.refresh(payment)
    write_audit_log(db, action="payment.update", entity_type="Payment", entity_id=payment.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(payment))
    db.commit()
    return payment


@router.post("/{payment_id}/mail/{template}")
def queue_payment_mail(payment_id: int, template: str, db: DbSession) -> dict:
    allowed_templates = {"payment_received"}
    if template not in allowed_templates:
        raise HTTPException(status_code=400, detail="Unknown payment mail template")
    payment = db.scalar(payment_detail_query().where(Payment.id == payment_id))
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    mail = create_payment_mail(payment, template, MailStatus.queued, db=db)
    if not mail:
        raise HTTPException(status_code=400, detail="Patient email is missing")
    db.add(mail)
    db.commit()
    return {"message": "Payment mail queued", "template": template}


@router.delete("/{payment_id}")
def delete_payment(payment_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    payment = db.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    old_value = model_snapshot(payment)
    invoice_id = payment.invoice_id
    db.delete(payment)
    db.flush()
    sync_invoice_paid_amount(db, invoice_id)
    write_audit_log(db, action="payment.delete", entity_type="Payment", entity_id=payment_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Payment deleted"}
