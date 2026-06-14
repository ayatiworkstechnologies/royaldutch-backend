from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import Invoice
from app.models.booking import Booking
from app.models.enums import InvoiceStatus, PaymentStatus
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff


def _range_filter(query, column, date_from: date | None, date_to: date | None):
    if date_from:
        query = query.where(column >= date_from)
    if date_to:
        query = query.where(column <= date_to)
    return query


def reporting_summary(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    status_rows = db.execute(
        _range_filter(
            select(Booking.status, func.count(Booking.id)).group_by(Booking.status),
            Booking.booking_date,
            date_from,
            date_to,
        )
    ).all()
    top_services = db.execute(
        _range_filter(
            select(Service.name, func.count(Booking.id).label("count"))
            .join(Booking, Booking.service_id == Service.id)
            .group_by(Service.id, Service.name)
            .order_by(func.count(Booking.id).desc())
            .limit(10),
            Booking.booking_date,
            date_from,
            date_to,
        )
    ).all()
    invoice_revenue = db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(Invoice.status != InvoiceStatus.cancelled))
    collected_revenue = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.payment_status.in_({PaymentStatus.paid, PaymentStatus.partially_paid})))
    refunded_revenue = db.scalar(select(func.coalesce(func.sum(Payment.refund_amount), 0)).where(Payment.refund_amount > 0))
    patient_query = select(func.count()).select_from(Patient)
    if date_from:
        patient_query = patient_query.where(func.date(Patient.created_at) >= date_from)
    if date_to:
        patient_query = patient_query.where(func.date(Patient.created_at) <= date_to)
    return {
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
        "bookings_by_status": {str(status): count for status, count in status_rows},
        "revenue": {
            "invoice_revenue": Decimal(str(invoice_revenue or 0)),
            "collected_revenue": Decimal(str(collected_revenue or 0)),
            "refunded_revenue": Decimal(str(refunded_revenue or 0)),
            "net_revenue": Decimal(str((collected_revenue or 0) - (refunded_revenue or 0))),
        },
        "top_services": [{"service": name, "count": count} for name, count in top_services],
        "new_patients": db.scalar(patient_query) or 0,
    }


def operational_report(db: Session, date_from: date | None = None, date_to: date | None = None) -> dict:
    bookings_by_day = db.execute(
        _range_filter(
            select(Booking.booking_date, func.count(Booking.id)).group_by(Booking.booking_date).order_by(Booking.booking_date),
            Booking.booking_date,
            date_from,
            date_to,
        )
    ).all()
    staff_rows = db.execute(
        _range_filter(
            select(Staff.name, func.count(Booking.id)).join(Booking, Booking.staff_id == Staff.id).group_by(Staff.id, Staff.name),
            Booking.booking_date,
            date_from,
            date_to,
        )
    ).all()
    payment_rows = db.execute(select(Payment.payment_method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0)).group_by(Payment.payment_method)).all()
    return {
        "bookings_by_day": [{"date": item_date.isoformat(), "count": count} for item_date, count in bookings_by_day],
        "staff_utilization": [{"staff": name, "bookings": count} for name, count in staff_rows],
        "payment_mix": [{"method": str(method), "count": count, "amount": Decimal(str(amount or 0))} for method, count, amount in payment_rows],
    }
