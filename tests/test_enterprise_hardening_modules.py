import os
import tempfile
from datetime import date
from pathlib import Path

test_db_path = Path(tempfile.gettempdir()) / "royalduch_test_enterprise.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import engine, SessionLocal
from app.main import app
from app.models.category import Category
from app.models.enums import RecordStatus, UserRole
from app.models.patient import Patient
from app.models.service import Service
from app.models.user import User


def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_admin_and_patient():
    reset_db()
    with SessionLocal() as db:
        admin = db.query(User).filter(User.email == "admin-hardening@example.com").first()
        if not admin:
            admin = User(
                name="Admin",
                email="admin-hardening@example.com",
                hashed_password=hash_password("AdminPass123"),
                role=UserRole.admin,
                is_active=True,
            )
            db.add(admin)
        patient = db.query(Patient).filter(Patient.phone == "+971500000001").first()
        if not patient:
            patient = Patient(full_name="Test Patient", email="patient@example.com", phone="+971500000001")
            db.add(patient)
        category = db.query(Category).filter(Category.slug == "hardening").first()
        if not category:
            category = Category(name="Hardening", slug="hardening", status=RecordStatus.active)
            db.add(category)
            db.flush()
        service = db.query(Service).filter(Service.slug == "hardening-service").first()
        if not service:
            db.add(
                Service(
                    category_id=category.id,
                    name="Hardening Service",
                    slug="hardening-service",
                    status=RecordStatus.active,
                    currency="AED",
                )
            )
        db.commit()
        return patient.id


def auth_headers(client: TestClient):
    response = client.post("/api/v1/auth/login", json={"email": "admin-hardening@example.com", "password": "AdminPass123"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["refresh_token"]
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["refresh_token"]


def test_refresh_token_rotation_and_logout():
    seed_admin_and_patient()
    client = TestClient(app)
    _, refresh_token = auth_headers(client)

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]
    assert refreshed.json()["refresh_token"] != refresh_token

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert reused.status_code == 401

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]})
    assert logout.status_code == 200


def test_patient_documents_and_admin_users():
    patient_id = seed_admin_and_patient()
    client = TestClient(app)
    headers, _ = auth_headers(client)

    created = client.post(
        f"/api/v1/patients/{patient_id}/documents",
        headers=headers,
        json={
            "title": "Consent Form",
            "document_type": "consent",
            "file_name": "consent.pdf",
            "content_type": "application/pdf",
            "external_url": "https://example.com/consent.pdf",
        },
    )
    assert created.status_code == 200
    document_id = created.json()["id"]

    listed = client.get(f"/api/v1/patients/{patient_id}/documents", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == document_id for item in listed.json())

    admin_user = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={"name": "Reports User", "email": "reports-user@example.com", "password": "Password123", "role": "accountant"},
    )
    assert admin_user.status_code == 200
    assert admin_user.json()["role"] == "accountant"


def test_whatsapp_reporting_and_trace_headers():
    seed_admin_and_patient()
    client = TestClient(app)
    headers, _ = auth_headers(client)
    headers["X-Correlation-ID"] = "test-correlation-id"

    sent = client.post(
        "/api/v1/whatsapp/send",
        headers=headers,
        json={"recipient_phone": "+971500000001", "message": "Appointment reminder"},
    )
    assert sent.status_code == 200
    assert sent.json()["status"] == "sent"
    assert sent.headers["X-Correlation-ID"] == "test-correlation-id"

    summary = client.get(f"/api/v1/reports/summary?date_from={date.today().isoformat()}", headers=headers)
    assert summary.status_code == 200
    assert "bookings_by_status" in summary.json()

    operations = client.get("/api/v1/reports/operations", headers=headers)
    assert operations.status_code == 200
    assert "payment_mix" in operations.json()
