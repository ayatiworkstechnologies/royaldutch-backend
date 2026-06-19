import os
import subprocess
import sys
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import inspect, select

os.environ["DATABASE_URL"] = f"sqlite:///{(Path(tempfile.gettempdir()) / 'royalduch_test_qa.db').as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

from app.core import rate_limit as rate_limit_module
from app.core.config import get_settings
from app.core.permissions import has_permission
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.audit_log import AuditLog
from app.models.auth_otp import AuthOtp
from app.models.billing import Invoice
from app.models.booking import BookingSlotLock
from app.models.category import Category
from app.models.enums import BookingStatus, InvoiceStatus, MailStatus, PaymentMethod, PaymentStatus, RecordStatus, UserRole
from app.models.mail import MailMessage
from app.models.patient import Patient
from app.models.payment import Payment
from app.models.service import Service
from app.models.staff import Staff, StaffAvailability
from app.models.user import User
from app.services.booking_service import available_slots
from app.services.mail_queue_service import claim_queued_mail, process_claimed_mail, recover_stale_processing_mail
from app.services.smtp_service import send_mail_message


def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def auth_headers_for(email: str = "admin@royaldutch.ae", password: str = "Admin@12345") -> dict[str, str]:
    with TestClient(app) as client:
        response = client.post("/api/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}


def token_headers(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


def next_workday() -> date:
    today = date.today()
    delta = (0 - today.weekday()) % 7 or 7
    return today + timedelta(days=delta)


def seed_role_user(role: UserRole, email: str) -> User:
    with SessionLocal() as db:
        user = User(name=role.value, email=email, role=role, hashed_password=hash_password("Password123"), is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


def seed_bookable_service() -> tuple[int, int, date]:
    reset_db()
    booking_date = next_workday()
    with SessionLocal() as db:
        category = Category(name="QA Category", slug="qa-category")
        service = Service(
            category=category,
            name="QA Service",
            slug="qa-service",
            duration_minutes=30,
            price=Decimal("125.00"),
            currency="AED",
        )
        staff = Staff(name="QA Doctor", role="Doctor")
        staff.services = [service]
        staff.availability = [
            StaffAvailability(
                day_of_week=booking_date.weekday(),
                start_time=time(9, 0),
                end_time=time(12, 0),
                break_start_time=time(10, 0),
                break_end_time=time(10, 30),
            )
        ]
        db.add_all([category, service, staff])
        db.commit()
        return service.id, staff.id, booking_date


def create_booking_payload(service_id: int, staff_id: int, booking_date: date, phone: str = "+971555000111", slot: str = "09:00"):
    return {
        "service_id": service_id,
        "staff_id": staff_id,
        "booking_date": booking_date.isoformat(),
        "booking_time": slot,
        "patient": {"full_name": "QA Patient", "email": f"{phone[-4:]}@example.com", "phone": phone},
        "first_visit": True,
    }


def test_auth_otp_google_and_production_boundaries(monkeypatch):
    reset_db()
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.post("/api/auth/login", json={"email": "admin@royaldutch.ae", "password": "bad"}).status_code == 401

        registered = client.post(
            "/api/auth/register",
            json={"name": "QA Customer", "email": "qa-customer@example.com", "phone": "+971555010001", "password": "Password123"},
        )
        assert registered.status_code == 201, registered.text
        assert client.post("/api/auth/register", json={"name": "QA Customer", "email": "qa-customer@example.com", "password": "Password123"}).status_code == 400
        assert client.post("/api/auth/login", json={"email": "qa-customer@example.com", "password": "Password123"}).status_code == 200

        otp_response = client.post("/api/auth/otp/request", json={"email": "otp-qa@example.com"})
        assert otp_response.status_code == 200, otp_response.text
        assert "dev_code" in otp_response.json()
        assert client.post("/api/auth/otp/verify", json={"email": "otp-qa@example.com", "code": "000000"}).status_code == 401
        assert client.post("/api/auth/otp/verify", json={"email": "otp-qa@example.com", "code": otp_response.json()["dev_code"]}).status_code == 200
        assert client.post("/api/auth/google", json={"credential": "dev-google:google-qa@example.com:Google QA"}).status_code == 200

    with SessionLocal() as db:
        expired = AuthOtp(email="expired@example.com", code_hash=hash_password("123456"), expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
        db.add(expired)
        db.commit()
    with TestClient(app) as client:
        assert client.post("/api/auth/otp/verify", json={"email": "expired@example.com", "code": "123456"}).status_code == 401

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "x" * 40)
    get_settings.cache_clear()
    with TestClient(app) as client:
        prod_otp = client.post("/api/auth/otp/request", json={"email": "prod-otp@example.com"})
        assert prod_otp.status_code == 200, prod_otp.text
        assert "dev_code" not in prod_otp.json()
        assert client.post("/api/auth/google", json={"credential": "dev-google:prod@example.com:Prod"}).status_code in {400, 401}
        assert client.post("/api/auth/ensure-admin").status_code == 403
    monkeypatch.setenv("APP_ENV", "local")
    get_settings.cache_clear()


def test_rate_limiting_memory_and_redis_paths(monkeypatch):
    reset_db()
    with TestClient(app) as client:
        for _ in range(3):
            assert client.post("/api/auth/otp/request", json={"email": "limited@example.com"}).status_code == 200
        assert client.post("/api/auth/otp/request", json={"email": "limited@example.com"}).status_code == 429

    class FakeRedis:
        def __init__(self):
            self.counts = {}

        def incr(self, key):
            self.counts[key] = self.counts.get(key, 0) + 1
            return self.counts[key]

        def expire(self, key, seconds):
            return True

    fake = FakeRedis()
    monkeypatch.setenv("REDIS_URL", "redis://example/0")
    get_settings.cache_clear()
    monkeypatch.setattr(rate_limit_module, "redis_client", lambda url: fake)
    rate_limit_module.rate_limit("qa-redis", 2, 60)
    rate_limit_module.rate_limit("qa-redis", 2, 60)
    with pytest.raises(Exception):
        rate_limit_module.rate_limit("qa-redis", 2, 60)
    monkeypatch.setenv("REDIS_URL", "")
    get_settings.cache_clear()


def test_role_permissions_and_admin_route_boundaries():
    reset_db()
    roles = {
        UserRole.super_admin: "super@example.com",
        UserRole.admin: "admin-role@example.com",
        UserRole.receptionist: "reception@example.com",
        UserRole.doctor: "doctor@example.com",
        UserRole.accountant: "accountant@example.com",
        UserRole.marketing: "marketing@example.com",
        UserRole.customer: "customer-role@example.com",
    }
    users = {role: seed_role_user(role, email) for role, email in roles.items()}
    assert has_permission(users[UserRole.accountant], "billing.manage")
    assert not has_permission(users[UserRole.accountant], "mail.manage")
    assert has_permission(users[UserRole.marketing], "mail.manage")
    assert not has_permission(users[UserRole.marketing], "billing.manage")

    with TestClient(app) as client:
        assert client.get("/api/billing", headers=token_headers(users[UserRole.accountant].id)).status_code == 200
        assert client.get("/api/mail", headers=token_headers(users[UserRole.accountant].id)).status_code == 403
        assert client.get("/api/mail", headers=token_headers(users[UserRole.marketing].id)).status_code == 200
        assert client.get("/api/dashboard", headers=token_headers(users[UserRole.customer].id)).status_code == 403
        assert client.get("/api/audit-logs", headers=token_headers(users[UserRole.admin].id)).status_code == 403
        assert client.get("/api/audit-logs", headers=token_headers(users[UserRole.super_admin].id)).status_code == 200


def test_category_service_staff_booking_slots_and_locks():
    service_id, staff_id, booking_date = seed_bookable_service()
    with TestClient(app) as client:
        slots = client.get("/api/bookings/slots", params={"service_id": service_id, "selected_date": booking_date.isoformat(), "staff_id": staff_id})
        assert slots.status_code == 200
        assert "09:00" in slots.json()["slots"]
        assert "10:00" not in slots.json()["slots"]

        first = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date))
        assert first.status_code == 200, first.text
        assert first.json()["booking_code"].startswith(f"RD-{booking_date:%y%m%d}-")
        duplicate = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date, "+971555000222"))
        assert duplicate.status_code == 409

        admin_headers = auth_headers_for()
        assert client.patch(f"/api/bookings/{first.json()['id']}/status", headers=admin_headers, json={"status": "confirmed"}).status_code == 200
        with SessionLocal() as db:
            assert db.query(BookingSlotLock).count() == 1
        assert client.patch(f"/api/bookings/{first.json()['id']}/status", headers=admin_headers, json={"status": "completed"}).status_code == 200

    with SessionLocal() as db:
        assert db.query(BookingSlotLock).count() == 0
        service = db.get(Service, service_id)
        service.status = RecordStatus.inactive
        db.commit()
    with TestClient(app) as client:
        inactive = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date, "+971555000333", "11:00"))
        assert inactive.status_code == 404


def test_cancelled_booking_releases_slot_and_reschedule_updates_lock():
    service_id, staff_id, booking_date = seed_bookable_service()
    with TestClient(app) as client:
        admin_headers = auth_headers_for()
        booking = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date)).json()
        rescheduled = client.patch(
            f"/api/bookings/{booking['id']}",
            headers=admin_headers,
            json={"booking_time": "09:30"},
        )
        assert rescheduled.status_code == 200, rescheduled.text
        with SessionLocal() as db:
            lock = db.scalar(select(BookingSlotLock).where(BookingSlotLock.booking_id == booking["id"]))
            assert str(lock.booking_time) == "09:30:00"
        cancelled = client.patch(f"/api/bookings/{booking['id']}/status", headers=admin_headers, json={"status": "cancelled"})
        assert cancelled.status_code == 200, cancelled.text
        with SessionLocal() as db:
            assert db.scalar(select(BookingSlotLock).where(BookingSlotLock.booking_id == booking["id"])) is None
        replacement = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date, "+971555000444", "09:30"))
        assert replacement.status_code == 200, replacement.text


def test_billing_payment_pdf_dashboard_and_audit_flow():
    service_id, staff_id, booking_date = seed_bookable_service()
    with TestClient(app) as client:
        admin_headers = auth_headers_for()
        booking = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date)).json()
        invoice = client.post(f"/api/billing/from-booking/{booking['id']}", headers=admin_headers, json={"discount_amount": "5.00", "tax_amount": "10.00"})
        assert invoice.status_code == 200, invoice.text
        invoice_body = invoice.json()
        assert invoice_body["total_amount"] == "130.00"
        same_invoice = client.post(f"/api/billing/from-booking/{booking['id']}", headers=admin_headers, json={})
        assert same_invoice.json()["id"] == invoice_body["id"]
        assert client.get(f"/api/billing/{invoice_body['id']}/pdf", headers=admin_headers).content.startswith(b"%PDF")

        payment = client.post(
            "/api/payments",
            headers=admin_headers,
            json={"booking_id": booking["id"], "invoice_id": invoice_body["id"], "amount": "50.00", "payment_status": "paid", "payment_method": "pay_at_clinic"},
        )
        assert payment.status_code == 200, payment.text
        updated_invoice = client.get(f"/api/billing/{invoice_body['id']}", headers=admin_headers).json()
        assert updated_invoice["status"] == "partially_paid"
        assert updated_invoice["paid_amount"] == "50.00"
        assert client.patch(f"/api/payments/{payment.json()['id']}", headers=admin_headers, json={"amount": "130.00"}).status_code == 200
        assert client.post(f"/api/payments/{payment.json()['id']}/mail/payment_received", headers=admin_headers).status_code == 200
        dashboard = client.get("/api/dashboard", headers=admin_headers).json()
        assert dashboard["total_revenue"] == dashboard["net_revenue"]

    with SessionLocal() as db:
        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"invoice.create", "payment.create", "payment.update"} <= actions


def test_mail_queue_success_failure_stale_lock_and_smtp_safety(monkeypatch):
    reset_db()
    sent = []

    def successful_send(mail, attachments=None):
        sent.append(mail.id)
        mail.status = MailStatus.sent
        mail.error_message = None
        return mail

    monkeypatch.setattr("app.services.mail_queue_service.send_mail_message", successful_send)
    with SessionLocal() as db:
        mail = MailMessage(recipient_email="qa@example.com", subject="QA", body="Body", status=MailStatus.queued)
        db.add(mail)
        db.commit()
        claimed = claim_queued_mail(db)
        assert claimed[0].status == MailStatus.processing
        assert claimed[0].lock_token
        assert claim_queued_mail(db) == []
        process_claimed_mail(db, claimed[0])
        db.commit()
        assert sent == [mail.id]
        assert claimed[0].status == MailStatus.sent
        assert claimed[0].lock_token is None

        stale = MailMessage(
            recipient_email="stale@example.com",
            subject="Stale",
            body="Body",
            status=MailStatus.processing,
            retry_count=1,
            locked_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            lock_token="stale-token",
        )
        db.add(stale)
        db.commit()
        assert recover_stale_processing_mail(db, stale_minutes=15) == 1
        db.refresh(stale)
        assert stale.status == MailStatus.queued
        assert stale.lock_token is None

    unsafe = MailMessage(recipient_email="bad-email", subject="Bad", body="Body")
    send_mail_message(unsafe)
    assert unsafe.status == MailStatus.failed


def test_email_template_notification_audit_pagination_and_request_id():
    reset_db()
    with TestClient(app) as client:
        admin_headers = auth_headers_for()
        admin_headers["X-Request-ID"] = "qa-request-id"
        seeded = client.post("/api/email-templates/seed-defaults", headers=admin_headers)
        assert seeded.status_code == 200, seeded.text
        template = client.post("/api/email-templates", headers=admin_headers, json={"name": "QA Template", "slug": "qa-template", "subject": "Hi", "body": "Hello"})
        assert template.status_code == 200, template.text
        assert client.patch(f"/api/email-templates/{template.json()['id']}", headers=admin_headers, json={"subject": "Updated"}).status_code == 200
        notification = client.post("/api/notifications", headers=admin_headers, json={"channel": "dashboard", "recipient": "admin", "subject": "QA", "message": "Message"})
        assert notification.status_code == 200, notification.text
        assert client.patch(f"/api/notifications/{notification.json()['id']}", headers=admin_headers, json={"status": "sent"}).status_code == 200

        for endpoint in ["/api/patients", "/api/billing", "/api/payments", "/api/mail", "/api/notifications"]:
            plain = client.get(endpoint, headers=admin_headers)
            paged = client.get(f"{endpoint}?page=1&limit=2", headers=admin_headers)
            assert plain.status_code == 200, plain.text
            assert isinstance(plain.json(), list)
            assert set(paged.json()) == {"items", "total", "page", "limit", "pages"}

        with SessionLocal() as db:
            admin = db.scalar(select(User).where(User.email == "admin@royaldutch.ae"))
            admin.role = UserRole.super_admin
            db.commit()
        super_headers = auth_headers_for()
        audit_paged = client.get("/api/audit-logs?page=1&limit=5&action=email_template.seed_defaults", headers=super_headers)
        assert audit_paged.status_code == 200, audit_paged.text
        assert set(audit_paged.json()) == {"items", "total", "page", "limit", "pages"}
        assert client.delete(f"/api/email-templates/{template.json()['id']}", headers=super_headers).status_code == 200

    with SessionLocal() as db:
        actions = {row.action for row in db.query(AuditLog).all()}
        assert {"email_template.seed_defaults", "email_template.create", "email_template.update", "notification.create", "notification.update"} <= actions
        assert db.query(AuditLog).filter(AuditLog.request_id == "qa-request-id").count() >= 1


def test_customer_self_service_and_jwt_security_boundaries():
    service_id, staff_id, booking_date = seed_bookable_service()
    with TestClient(app) as client:
        admin_headers = auth_headers_for()
        booking = client.post("/api/bookings", json=create_booking_payload(service_id, staff_id, booking_date, phone="+971555099999")).json()
        invoice = client.post(f"/api/billing/from-booking/{booking['id']}", headers=admin_headers, json={}).json()
        otp = client.post("/api/auth/otp/request", json={"email": "9999@example.com"}).json()
        customer_token = client.post("/api/auth/otp/verify", json={"email": "9999@example.com", "code": otp["dev_code"]}).json()["access_token"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        assert client.get("/api/account/me", headers=customer_headers).status_code == 200
        assert client.patch("/api/account/me", headers=customer_headers, json={"full_name": "Updated QA", "phone": "+971555099999"}).status_code == 200
        assert client.get("/api/account/invoices", headers=customer_headers).status_code == 200
        assert client.get(f"/api/account/invoices/{invoice['id']}/pdf", headers=customer_headers).content.startswith(b"%PDF")
        assert client.get("/api/dashboard", headers=customer_headers).status_code == 403

        expired = jwt.encode({"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, get_settings().secret_key, algorithm="HS256")
        assert client.get("/api/dashboard", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
        assert client.get("/api/dashboard", headers={"Authorization": "Bearer not-a-jwt"}).status_code == 401


def test_alembic_clean_upgrade_and_existing_stamp_flow(tmp_path):
    clean_db = tmp_path / "clean.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{clean_db.as_posix()}"
    subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[1], env=env, check=True)
    from sqlalchemy import create_engine

    migrated_engine = create_engine(env["DATABASE_URL"])
    inspector = inspect(migrated_engine)
    assert "booking_slot_locks" in inspector.get_table_names()
    assert "audit_logs" in inspector.get_table_names()
    assert "uq_booking_slot_lock" in {constraint["name"] for constraint in inspector.get_unique_constraints("booking_slot_locks")}

    existing_db = tmp_path / "existing.db"
    existing_env = os.environ.copy()
    existing_env["DATABASE_URL"] = f"sqlite:///{existing_db.as_posix()}"
    create_script = "from app.db.base import Base; from app.db.session import engine; import app.models; Base.metadata.create_all(bind=engine)"
    subprocess.run([sys.executable, "-c", create_script], cwd=Path(__file__).resolve().parents[1], env=existing_env, check=True)
    subprocess.run([sys.executable, "scripts/verify_schema_for_stamp.py"], cwd=Path(__file__).resolve().parents[1], env=existing_env, check=True)
    subprocess.run([sys.executable, "scripts/stamp_existing_schema.py"], cwd=Path(__file__).resolve().parents[1], env=existing_env, check=True)
    subprocess.run(["alembic", "upgrade", "head"], cwd=Path(__file__).resolve().parents[1], env=existing_env, check=True)
