from datetime import datetime, timedelta, timezone
import random

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.auth_otp import AuthOtp
from app.models.enums import UserRole
from app.models.mail import MailMessage
from app.models.patient import Patient
from app.models.user import User
from app.models.enums import MailStatus
from app.schemas.auth import GoogleLoginRequest, LoginRequest, OtpRequest, OtpVerifyRequest, RegisterRequest, TokenResponse
from app.seed.clinic_data import seed_database
from app.services.email_template_service import seed_default_email_templates
from app.services.smtp_service import send_mail_message
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
DEFAULT_ADMIN_EMAIL = "admin@royaldutch.ae"
OTP_EXPIRE_MINUTES = 10


def customer_token_response(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user.id), role=user.role, name=user.name, email=user.email)


def get_or_create_customer(db: DbSession, email: str, name: str | None = None) -> User:
    email = email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    patient = db.scalar(select(Patient).where(Patient.email == email))
    if not user:
        user = User(
            name=(name or (patient.full_name if patient else email.split("@", 1)[0])).strip(),
            email=email,
            hashed_password=None,
            role=UserRole.customer,
            is_active=True,
        )
        db.add(user)
        db.flush()
    elif name and (not user.name or user.name == user.email.split("@", 1)[0]):
        user.name = name.strip()
    if patient and not patient.user_id:
        patient.user_id = user.id
    return user


def upsert_customer_patient(db: DbSession, user: User, name: str | None = None, phone: str | None = None) -> None:
    clean_name = name.strip() if name else None
    clean_phone = phone.strip() if phone else None
    if clean_name and (not user.name or user.name == user.email.split("@", 1)[0]):
        user.name = clean_name
    if not clean_phone:
        return

    patient = db.scalar(select(Patient).where(Patient.phone == clean_phone))
    if not patient:
        patient = db.scalar(select(Patient).where(Patient.email == user.email))
    if patient:
        patient.full_name = clean_name or patient.full_name or user.name
        patient.email = user.email
        patient.phone = clean_phone
        patient.user_id = user.id
    else:
        db.add(Patient(full_name=clean_name or user.name or user.email, email=user.email, phone=clean_phone, user_id=user.id))


def link_patient_by_email(db: DbSession, user: User) -> None:
    patient = db.scalar(select(Patient).where(Patient.email == user.email))
    if patient and not patient.user_id:
        patient.user_id = user.id


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == data.email.lower().strip()))
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    return customer_token_response(user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> TokenResponse:
    email = data.email.lower().strip()
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    user = db.scalar(select(User).where(User.email == email))
    if user and user.hashed_password:
        raise HTTPException(status_code=400, detail="Account already exists. Please sign in.")

    if user:
        user.name = data.name.strip()
        user.hashed_password = hash_password(data.password)
        user.role = UserRole.customer
        user.is_active = True
    else:
        user = User(
            name=data.name.strip(),
            email=email,
            hashed_password=hash_password(data.password),
            role=UserRole.customer,
            is_active=True,
        )
        db.add(user)
        db.flush()

    if data.phone:
        patient = db.scalar(select(Patient).where(Patient.phone == data.phone))
        if patient:
            patient.full_name = data.name.strip()
            patient.email = email
            patient.user_id = user.id
        elif not user.patient:
            db.add(Patient(full_name=data.name.strip(), email=email, phone=data.phone, user_id=user.id))

    db.commit()
    db.refresh(user)
    return customer_token_response(user)


@router.post("/otp/request")
def request_otp(data: OtpRequest, db: DbSession) -> dict:
    email = data.email.lower().strip()
    code = f"{random.SystemRandom().randint(100000, 999999)}"
    otp = AuthOtp(
        email=email,
        code_hash=hash_password(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp)

    mail = MailMessage(
        recipient_email=email,
        recipient_name=None,
        subject="Your Royal Dutch login code",
        body=(
            "<html><body style=\"font-family:Arial,sans-serif;background:#f8fafc;padding:24px;\">"
            "<div style=\"max-width:520px;margin:auto;background:white;border:1px solid #e5e7eb;border-radius:14px;padding:24px;\">"
            "<h2 style=\"margin:0;color:#0f172a;\">Your login code</h2>"
            f"<p style=\"color:#475569;\">Use this code to open your customer portal. It expires in {OTP_EXPIRE_MINUTES} minutes.</p>"
            f"<div style=\"font-size:32px;font-weight:800;letter-spacing:8px;color:#5b0f4d;\">{code}</div>"
            "</div></body></html>"
        ),
        status=MailStatus.queued,
    )
    send_mail_message(mail)
    db.add(mail)
    db.commit()
    response = {"message": "Login code sent if the email can receive mail", "mail_status": mail.status}
    if get_settings().app_env != "production":
        response["dev_code"] = code
    return response


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(data: OtpVerifyRequest, db: DbSession) -> TokenResponse:
    email = data.email.lower().strip()
    otps = db.scalars(
        select(AuthOtp)
        .where(AuthOtp.email == email, AuthOtp.used == False)  # noqa: E712
        .order_by(AuthOtp.created_at.desc())
        .limit(5)
    ).all()
    now = datetime.now(timezone.utc)
    otp = next(
        (
            item
            for item in otps
            if (item.expires_at if item.expires_at.tzinfo else item.expires_at.replace(tzinfo=timezone.utc)) >= now
            and verify_password(data.code, item.code_hash)
        ),
        None,
    )
    if not otp:
        raise HTTPException(status_code=401, detail="Invalid or expired login code")
    otp.used = True

    user = get_or_create_customer(db, email, data.name)
    upsert_customer_patient(db, user, data.name, data.phone)
    db.commit()
    db.refresh(user)
    return customer_token_response(user)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: DbSession) -> TokenResponse:
    settings = get_settings()

    if settings.app_env != "production" and data.credential.startswith("dev-google:"):
        parts = data.credential.split(":", 2)
        email = parts[1].lower().strip()
        name = parts[2].strip() if len(parts) > 2 else email.split("@", 1)[0]
    else:
        if not settings.google_client_id:
            raise HTTPException(status_code=400, detail="Google login is not configured")
        try:
            from google.auth.transport import requests as google_requests
            from google.oauth2 import id_token

            payload = id_token.verify_oauth2_token(
                data.credential,
                google_requests.Request(),
                settings.google_client_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=401, detail="Invalid Google credential") from exc
        if not payload.get("email_verified"):
            raise HTTPException(status_code=401, detail="Google email is not verified")
        email = payload["email"].lower().strip()
        name = payload.get("name") or email.split("@", 1)[0]

    user = get_or_create_customer(db, email, name)
    link_patient_by_email(db, user)
    db.commit()
    db.refresh(user)
    return customer_token_response(user)


@router.get("/admin-status")
def admin_status(db: DbSession) -> dict:
    admin = db.scalar(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
    return {
        "exists": bool(admin),
        "email": admin.email if admin else None,
        "is_active": admin.is_active if admin else False,
        "default_password_ok": verify_password("Admin@12345", admin.hashed_password) if admin and admin.hashed_password else False,
    }


@router.post("/ensure-admin")
def ensure_admin(db: DbSession) -> dict:
    seed_database(db)
    seed_default_email_templates(db)
    admin = db.scalar(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
    return {
        "message": "Admin and seed data checked",
        "exists": bool(admin),
        "default_password_ok": verify_password("Admin@12345", admin.hashed_password) if admin and admin.hashed_password else False,
    }
