import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

test_db_path = Path(tempfile.gettempdir()) / "royalduch_test_api_flow.db"
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_FROM_EMAIL"] = ""
os.environ["SMTP_USERNAME"] = ""
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.models.patient import Patient
from app.models.user import User


def assert_ok(response, expected_status=200):
    assert response.status_code == expected_status, response.text
    return response.json()


def next_monday() -> date:
    today = date.today()
    days = (0 - today.weekday()) % 7
    if days == 0:
        days = 7
    return today + timedelta(days=days)


def auth_headers(client: TestClient) -> dict[str, str]:
    token = assert_ok(
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@royaldutch.ae", "password": "Admin@12345"},
        )
    )["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_backend_api_end_to_end_flow():
    Base.metadata.drop_all(bind=engine)

    with TestClient(app) as client:
        assert_ok(client.get("/health"))

        admin_status = assert_ok(client.get("/api/v1/auth/admin-status"))
        assert admin_status["exists"] is True
        assert admin_status["default_password_ok"] is True

        headers = auth_headers(client)

        customer = assert_ok(
            client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Flow Customer",
                    "email": "flow-customer@example.com",
                    "phone": "+971500000099",
                    "password": "Customer123",
                },
            ),
            201,
        )
        assert customer["role"] == "customer"
        assert_ok(
            client.post(
                "/api/v1/auth/login",
                json={"email": "flow-customer@example.com", "password": "Customer123"},
            )
        )
        duplicate = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Flow Customer",
                "email": "flow-customer@example.com",
                "phone": "+971500000099",
                "password": "Customer123",
            },
        )
        assert duplicate.status_code == 400
        otp_request = assert_ok(client.post("/api/v1/auth/otp/request", json={"email": "flow-customer@example.com"}))
        code = otp_request["dev_code"]
        otp_login = assert_ok(client.post("/api/v1/auth/otp/verify", json={"email": "flow-customer@example.com", "code": code}))
        assert otp_login["role"] == "customer"
        same_email_google = assert_ok(
            client.post(
                "/api/v1/auth/google",
                json={"credential": "dev-google:FLOW-CUSTOMER@example.com:Flow Google"},
            )
        )
        assert same_email_google["email"] == "flow-customer@example.com"
        otp_register_request = assert_ok(client.post("/api/v1/auth/otp/request", json={"email": "otp-register@example.com"}))
        otp_register = assert_ok(
            client.post(
                "/api/v1/auth/otp/verify",
                json={
                    "email": "otp-register@example.com",
                    "code": otp_register_request["dev_code"],
                    "name": "OTP Register Patient",
                    "phone": "+971500000098",
                },
            )
        )
        assert otp_register["name"] == "OTP Register Patient"
        google_login = assert_ok(
            client.post(
                "/api/v1/auth/google",
                json={"credential": "dev-google:google-customer@example.com:Google Customer"},
            )
        )
        assert google_login["email"] == "google-customer@example.com"
        assert google_login["role"] == "customer"

        settings = assert_ok(client.get("/api/v1/settings", headers=headers))
        assert settings["clinic_name"]
        settings = assert_ok(
            client.patch(
                "/api/v1/settings",
                headers=headers,
                json={
                    "clinic_name": "Royal Dutch Test Clinic",
                    "clinic_email": "billing@example.com",
                    "clinic_phone": "+971 555 000 000",
                    "clinic_address": "Test Clinic Road, Dubai",
                    "invoice_footer": "Thank you for testing.",
                    "invoice_terms": "Due on receipt.",
                    "tax_registration_number": "TRN-TEST",
                    "default_currency": "AED",
                },
            )
        )
        assert settings["clinic_name"] == "Royal Dutch Test Clinic"

        categories = assert_ok(client.get("/api/v1/categories"))
        assert categories
        category = assert_ok(
            client.post(
                "/api/v1/categories",
                headers=headers,
                json={
                    "name": "API Flow Category",
                    "slug": "api-flow-category",
                    "description": "Created by backend API flow test",
                },
            )
        )
        category = assert_ok(
            client.patch(
                f"/api/v1/categories/{category['id']}",
                headers=headers,
                json={"description": "Updated by backend API flow test"},
            )
        )

        service = assert_ok(
            client.post(
                "/api/v1/services",
                headers=headers,
                json={
                    "category_id": category["id"],
                    "name": "API Flow Service",
                    "slug": "api-flow-service",
                    "description": "Test service",
                    "duration_minutes": 30,
                    "price": "125.00",
                    "currency": "AED",
                },
            )
        )
        assert_ok(client.get("/api/v1/services"))
        assert_ok(client.get(f"/api/v1/services/{service['slug']}"))

        monday = next_monday()
        staff = assert_ok(
            client.post(
                "/api/v1/staff",
                headers=headers,
                json={
                    "name": "API Flow Specialist",
                    "email": "api-flow-specialist@example.com",
                    "phone": "+971500000001",
                    "role": "Specialist",
                    "specialization": "API Testing",
                    "service_ids": [service["id"]],
                    "availability": [
                        {
                            "day_of_week": monday.weekday(),
                            "start_time": "09:00",
                            "end_time": "17:00",
                            "break_start_time": "12:00",
                            "break_end_time": "13:00",
                        }
                    ],
                },
            )
        )
        assert_ok(client.get("/api/v1/staff"))

        slots = assert_ok(
            client.get(
                "/api/v1/bookings/slots",
                params={"service_id": service["id"], "selected_date": monday.isoformat()},
            )
        )["slots"]
        assert "09:00" in slots

        booking = assert_ok(
            client.post(
                "/api/v1/bookings",
                json={
                    "service_id": service["id"],
                    "staff_id": staff["id"],
                    "booking_date": monday.isoformat(),
                    "booking_time": "09:00",
                    "patient": {
                        "full_name": "API Flow Patient",
                        "email": "api-flow-patient@example.com",
                        "phone": "+971500000002",
                        "gender": "female",
                        "age": 31,
                    },
                    "notes": "End-to-end test booking",
                    "first_visit": True,
                },
            )
        )
        assert booking["status"] == "pending"

        assert_ok(client.get("/api/v1/bookings", headers=headers))
        assert_ok(client.get(f"/api/v1/bookings/{booking['id']}", headers=headers))
        assert_ok(
            client.get(
                "/api/v1/bookings/calendar",
                headers=headers,
                params={"start_date": monday.isoformat(), "end_date": monday.isoformat()},
            )
        )
        assert_ok(client.get("/api/v1/bookings/lookup", params={"phone": "+971500000002"}))

        confirmed = assert_ok(
            client.patch(
                f"/api/v1/bookings/{booking['id']}/status",
                headers=headers,
                json={"status": "confirmed"},
            )
        )
        assert confirmed["status"] == "confirmed"

        patient = assert_ok(client.get("/api/v1/patients", headers=headers, params={"phone": "+971500000002"}))[0]
        otp_patient = assert_ok(client.get("/api/v1/patients", headers=headers, params={"phone": "+971500000098"}))[0]
        assert otp_patient["full_name"] == "OTP Register Patient"
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(User).where(User.email == "flow-customer@example.com")) == 1
            linked_patient = db.scalar(select(Patient).where(Patient.email == "flow-customer@example.com"))
            linked_user = db.scalar(select(User).where(User.email == "flow-customer@example.com"))
            assert linked_patient.user_id == linked_user.id
        assert_ok(
            client.patch(
                f"/api/v1/patients/{patient['id']}",
                headers=headers,
                json={"notes": "Updated by API flow"},
            )
        )

        invoice = assert_ok(
            client.post(
                f"/api/v1/billing/from-booking/{booking['id']}",
                headers=headers,
                json={"notes": "Invoice from booking"},
            )
        )
        assert invoice["booking_id"] == booking["id"]
        assert_ok(client.get("/api/v1/billing", headers=headers))
        invoice = assert_ok(
            client.patch(
                f"/api/v1/billing/{invoice['id']}",
                headers=headers,
                json={"tax_amount": "5.00"},
            )
        )
        assert invoice["total_amount"] == "130.00"
        assert invoice["balance_due"] == "130.00"
        assert_ok(client.get(f"/api/v1/billing/{invoice['id']}", headers=headers))
        pdf_response = client.get(f"/api/v1/billing/{invoice['id']}/pdf", headers=headers)
        assert pdf_response.status_code == 200, pdf_response.text
        assert pdf_response.content.startswith(b"%PDF")
        customer_otp = assert_ok(client.post("/api/v1/auth/otp/request", json={"email": "api-flow-patient@example.com"}))
        customer_token = assert_ok(
            client.post(
                "/api/v1/auth/otp/verify",
                json={"email": "api-flow-patient@example.com", "code": customer_otp["dev_code"]},
            )
        )["access_token"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        customer_profile = assert_ok(client.get("/api/v1/account/me", headers=customer_headers))
        assert customer_profile["email"] == "api-flow-patient@example.com"
        customer_profile = assert_ok(
            client.patch(
                "/api/v1/account/me",
                headers=customer_headers,
                json={"full_name": "API Flow Patient Updated", "phone": "+971500000002", "age": 32, "gender": "female"},
            )
        )
        assert customer_profile["full_name"] == "API Flow Patient Updated"
        customer_invoices = assert_ok(client.get("/api/v1/account/invoices", headers=customer_headers))
        assert customer_invoices and customer_invoices[0]["invoice_number"] == invoice["invoice_number"]
        customer_pdf_response = client.get(f"/api/v1/account/invoices/{invoice['id']}/pdf", headers=customer_headers)
        assert customer_pdf_response.status_code == 200, customer_pdf_response.text
        assert customer_pdf_response.content.startswith(b"%PDF")
        assert_ok(client.post(f"/api/v1/billing/{invoice['id']}/mail/invoice_issued", headers=headers))
        send_result = assert_ok(client.post(f"/api/v1/billing/{invoice['id']}/send", headers=headers))
        assert send_result["status"] in {"sent", "failed"}

        payment = assert_ok(
            client.post(
                "/api/v1/payments",
                headers=headers,
                json={
                    "booking_id": booking["id"],
                    "invoice_id": invoice["id"],
                    "amount": "50.00",
                    "payment_method": "pay_at_clinic",
                    "payment_status": "paid",
                    "transaction_id": "api-flow-001",
                },
            )
        )
        assert_ok(client.get("/api/v1/payments", headers=headers))
        assert_ok(client.get(f"/api/v1/payments/{payment['id']}", headers=headers))
        synced_invoice = assert_ok(client.get("/api/v1/billing", headers=headers))[0]
        assert synced_invoice["paid_amount"] == "50.00"
        assert synced_invoice["balance_due"] == "80.00"
        assert synced_invoice["status"] == "partially_paid"
        assert_ok(client.post(f"/api/v1/payments/{payment['id']}/mail/payment_received", headers=headers))
        assert_ok(
            client.patch(
                f"/api/v1/payments/{payment['id']}",
                headers=headers,
                json={"payment_status": "partially_paid"},
            )
        )
        assert_ok(client.delete(f"/api/v1/payments/{payment['id']}", headers=headers))
        invoice_after_delete = assert_ok(client.get(f"/api/v1/billing/{invoice['id']}", headers=headers))
        assert invoice_after_delete["paid_amount"] == "0.00"
        assert invoice_after_delete["balance_due"] == "130.00"

        mail = assert_ok(
            client.post(
                "/api/v1/mail",
                headers=headers,
                json={
                    "recipient_email": "api-flow-patient@example.com",
                    "recipient_name": "API Flow Patient",
                    "subject": "API Flow Mail",
                    "body": "Body",
                    "status": "draft",
                },
            )
        )
        assert_ok(client.get("/api/v1/mail", headers=headers))
        assert_ok(
            client.patch(
                f"/api/v1/mail/{mail['id']}",
                headers=headers,
                json={"status": "queued"},
            )
        )
        assert_ok(client.post(f"/api/v1/bookings/{booking['id']}/mail/reminder", headers=headers))

        templates = assert_ok(client.get("/api/v1/email-templates", headers=headers))
        assert templates
        custom_template = assert_ok(
            client.post(
                "/api/v1/email-templates",
                headers=headers,
                json={
                    "name": "API Flow Template",
                    "slug": "api-flow-template",
                    "subject": "Hello {patient_name}",
                    "body": "Booking {booking_code}",
                },
            )
        )
        assert_ok(
            client.patch(
                f"/api/v1/email-templates/{custom_template['id']}",
                headers=headers,
                json={"subject": "Updated subject"},
            )
        )

        notification = assert_ok(
            client.post(
                "/api/v1/notifications",
                headers=headers,
                json={
                    "booking_id": booking["id"],
                    "channel": "dashboard",
                    "recipient": "admin",
                    "subject": "API Flow Notification",
                    "message": "Notification body",
                    "status": "queued",
                },
            )
        )
        assert_ok(client.get("/api/v1/notifications", headers=headers))
        assert_ok(
            client.patch(
                f"/api/v1/notifications/{notification['id']}",
                headers=headers,
                json={"status": "sent"},
            )
        )

        stats = assert_ok(client.get("/api/v1/dashboard", headers=headers))
        assert "pending_bookings" in stats

        assert_ok(client.patch(f"/api/v1/staff/{staff['id']}", headers=headers, json={"status": "inactive"}))
        assert_ok(client.delete(f"/api/v1/services/{service['id']}", headers=headers))
        assert_ok(client.delete(f"/api/v1/categories/{category['id']}", headers=headers))
        assert_ok(client.delete(f"/api/v1/mail/{mail['id']}", headers=headers))
        assert_ok(client.delete(f"/api/v1/email-templates/{custom_template['id']}", headers=headers))
