import os
import tempfile
from pathlib import Path

test_db_path = Path(tempfile.gettempdir()) / "royalduch_test_hardening.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.permissions import has_permission
from app.db.base import Base
from app.db.session import engine
from app.models.audit_log import AuditLog
from app.models.billing import Invoice, InvoiceItem
from app.models.booking import Booking, BookingSlotLock
from app.models.enums import BookingStatus, InvoiceStatus, PaymentMethod, PaymentStatus, UserRole
from app.main import app
from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.models.user import User
from app.services.mail_queue_service import MAX_MAIL_RETRIES, claim_queued_mail, process_claimed_mail
from app.services.booking_service import validate_status_transition
from app.core.security import create_access_token
from fastapi import HTTPException
import pytest
from datetime import date, time, timedelta
from decimal import Decimal


def test_admin_seed_endpoint_disabled_in_production(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    Base.metadata.drop_all(bind=engine)

    with TestClient(app) as client:
        response = client.post("/api/auth/ensure-admin")

    assert response.status_code == 403
    get_settings.cache_clear()


def test_login_rate_limit_applies():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        for _ in range(5):
            response = client.post(
                "/api/auth/login",
                json={"email": "missing@example.com", "password": "wrong-password"},
            )
            assert response.status_code == 401

        limited = client.post(
            "/api/auth/login",
            json={"email": "missing@example.com", "password": "wrong-password"},
        )

    assert limited.status_code == 429


def test_mail_claim_moves_message_to_processing():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        mail = MailMessage(
            recipient_email="patient@example.com",
            subject="Queued",
            body="Body",
            status=MailStatus.queued,
        )
        db.add(mail)
        db.commit()

        claimed = claim_queued_mail(db, limit=10)

        assert len(claimed) == 1
        assert claimed[0].status == MailStatus.processing
        assert claimed[0].locked_at is not None
        assert claim_queued_mail(db, limit=10) == []


def test_mail_retry_failure_reaches_max_without_duplicate_claim(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal

    calls = []

    def failing_send(mail, attachments=None):
        calls.append(mail.id)
        mail.status = MailStatus.failed
        mail.error_message = "SMTP refused"
        return mail

    monkeypatch.setattr("app.services.mail_queue_service.send_mail_message", failing_send)

    with SessionLocal() as db:
        mail = MailMessage(
            recipient_email="patient@example.com",
            subject="Queued",
            body="Body",
            status=MailStatus.queued,
        )
        db.add(mail)
        db.commit()
        mail_id = mail.id

        for attempt in range(MAX_MAIL_RETRIES):
            claimed = claim_queued_mail(db, limit=10, include_failed=True)
            assert [item.id for item in claimed] == [mail_id]
            assert claim_queued_mail(db, limit=10, include_failed=True) == []
            process_claimed_mail(db, claimed[0])
            db.commit()
            db.refresh(claimed[0])
            assert claimed[0].retry_count == attempt + 1
            assert claimed[0].status == MailStatus.failed
            assert claimed[0].error_message == "SMTP refused"

        assert claim_queued_mail(db, limit=10, include_failed=True) == []
        assert calls == [mail_id, mail_id, mail_id]


def test_invalid_booking_status_transition_is_rejected():
    with pytest.raises(HTTPException) as exc:
        validate_status_transition(BookingStatus.completed, BookingStatus.cancelled)
    assert exc.value.status_code == 409


def test_booking_slot_lock_blocks_duplicate_and_releases_on_cancel():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal
    from app.schemas.booking import BookingCreate
    from app.schemas.patient import PatientCreate
    from app.services.booking_service import create_booking, update_booking_status

    booking_date = date.today() + timedelta(days=(7 - date.today().weekday()))
    with SessionLocal() as db:
        service = Service(
            category_id=1,
            name="Lock Service",
            slug="lock-service",
            duration_minutes=30,
            price=Decimal("100.00"),
            currency="AED",
        )
        staff = Staff(name="Lock Staff", role="Doctor")
        staff.services = [service]
        staff.availability = [
            StaffAvailability(
                day_of_week=booking_date.weekday(),
                start_time=time(9, 0),
                end_time=time(17, 0),
            )
        ]
        from app.models.category import Category

        db.add(Category(id=1, name="Lock Category", slug="lock-category"))
        db.add_all([service, staff])
        db.commit()
        data = BookingCreate(
            service_id=service.id,
            staff_id=staff.id,
            booking_date=booking_date,
            booking_time=time(9, 0),
            patient=PatientCreate(full_name="Lock Patient", phone="+971500009999"),
        )
        booking = create_booking(db, data)
        assert db.query(BookingSlotLock).filter(BookingSlotLock.booking_id == booking.id).count() == 1

        with pytest.raises(HTTPException) as exc:
            create_booking(
                db,
                BookingCreate(
                    service_id=service.id,
                    staff_id=staff.id,
                    booking_date=booking_date,
                    booking_time=time(9, 0),
                    patient=PatientCreate(full_name="Other Patient", phone="+971500008888"),
                ),
            )
        assert exc.value.status_code == 409

        booking = db.get(Booking, booking.id)
        update_booking_status(db, booking, BookingStatus.cancelled)
        db.commit()
        assert db.query(BookingSlotLock).filter(BookingSlotLock.booking_id == booking.id).count() == 0


def test_permission_helper_keeps_admin_and_restricts_customer():
    class UserStub:
        role = UserRole.admin

    class CustomerStub:
        role = UserRole.customer

    assert has_permission(UserStub(), "settings.manage") is True
    assert has_permission(CustomerStub(), "settings.manage") is False


def test_paginated_categories_response_has_envelope():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        response = client.get("/api/patients?page=1&limit=2", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "limit", "pages"}
    assert body["page"] == 1
    assert body["limit"] == 2


def test_settings_update_creates_audit_log():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        response = client.patch(
            "/api/settings",
            headers={"Authorization": f"Bearer {token}", "X-Request-ID": "test-request-id"},
            json={"clinic_name": "Audit Clinic"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["X-Request-ID"] == "test-request-id"

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        audit = db.query(AuditLog).filter(AuditLog.action == "settings.update").one()
        assert audit.request_id == "test-request-id"


def test_patient_and_notification_writes_create_audit_logs():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        patient = client.post(
            "/api/patients",
            headers=headers,
            json={"full_name": "Audit Patient", "email": "audit-patient@example.com", "phone": "+971500001111"},
        )
        assert patient.status_code == 200, patient.text
        notification = client.post(
            "/api/notifications",
            headers=headers,
            json={"channel": "dashboard", "recipient": "admin", "subject": "Audit", "message": "Audit notification"},
        )
        assert notification.status_code == 200, notification.text

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        assert db.query(AuditLog).filter(AuditLog.action == "patient.create").count() == 1
        assert db.query(AuditLog).filter(AuditLog.action == "notification.create").count() == 1


def test_audit_logs_are_super_admin_only():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        admin_token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        denied = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert denied.status_code == 403

        from app.db.session import SessionLocal

        with SessionLocal() as db:
            admin = db.query(User).filter(User.email == "admin@royaldutch.ae").one()
            admin.role = UserRole.super_admin
            db.commit()

        super_token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        allowed = client.get("/api/audit-logs", headers={"Authorization": f"Bearer {super_token}"})
        assert allowed.status_code == 200, allowed.text


def test_customer_cannot_access_another_customer_invoice():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        user_a = User(name="A", email="a@example.com", role=UserRole.customer, is_active=True)
        user_b = User(name="B", email="b@example.com", role=UserRole.customer, is_active=True)
        db.add_all([user_a, user_b])
        db.flush()
        patient_b = Patient(full_name="Patient B", email="b@example.com", phone="+971500002222", user_id=user_b.id)
        db.add(patient_b)
        db.flush()
        invoice = Invoice(
            invoice_number="INV-TEST-B",
            patient_id=patient_b.id,
            issue_date=date.today(),
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("100.00"),
            paid_amount=Decimal("0"),
            balance_due=Decimal("100.00"),
            currency="AED",
            status=InvoiceStatus.issued,
        )
        invoice.items = [InvoiceItem(description="Test", quantity=1, unit_price=Decimal("100.00"), line_total=Decimal("100.00"))]
        db.add(invoice)
        db.commit()
        invoice_id = invoice.id
        token_a = create_access_token(user_a.id)

    with TestClient(app) as client:
        response = client.get(f"/api/account/invoices/{invoice_id}/pdf", headers={"Authorization": f"Bearer {token_a}"})

    assert response.status_code == 404


def test_refund_amount_reduces_dashboard_net_revenue():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        payment = Payment(
            amount=Decimal("100.00"),
            refund_amount=Decimal("25.00"),
            payment_method=PaymentMethod.pay_at_clinic,
            payment_status=PaymentStatus.paid,
        )
        db.add(payment)
        db.commit()

    with TestClient(app) as client:
        token = client.post(
            "/api/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        ).json()["access_token"]
        response = client.get("/api/dashboard", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["collected_revenue"] == "100.00"
    assert body["refunded_revenue"] == "25.00"
    assert body["net_revenue"] == "75.00"
    assert body["total_revenue"] == "75.00"
