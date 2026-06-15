from datetime import datetime, timedelta, timezone
import hashlib
import random
import secrets

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import client_ip, rate_limit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.auth_otp import AuthOtp
from app.models.enums import MailStatus, UserRole
from app.models.mail import MailMessage
from app.models.patient import Patient
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import GoogleLoginRequest, LoginRequest, OtpRequest, OtpVerifyRequest, RegisterRequest, TokenResponse
from app.seed.clinic_data import seed_database
from app.services.audit_service import write_audit_log
from app.services.email_template_service import seed_default_email_templates
from app.services.smtp_service import send_mail_message

DEFAULT_ADMIN_EMAIL = "admin@royaldutch.ae"
OTP_EXPIRE_MINUTES = 10


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user: User, request: Request | None = None) -> str:
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_hash(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
            created_by_ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
    return raw_token


def customer_token_response(user: User, db: Session | None = None, request: Request | None = None) -> TokenResponse:
    refresh_token = create_refresh_token(db, user, request) if db else None
    return TokenResponse(
        access_token=create_access_token(user.id),
        role=user.role,
        name=user.name,
        email=user.email,
        refresh_token=refresh_token,
    )


def get_or_create_customer(db: Session, email: str, name: str | None = None) -> User:
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


def upsert_customer_patient(db: Session, user: User, name: str | None = None, phone: str | None = None) -> None:
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


def link_patient_by_email(db: Session, user: User) -> None:
    patient = db.scalar(select(Patient).where(Patient.email == user.email))
    if patient and not patient.user_id:
        patient.user_id = user.id


def login_with_password(db: Session, data: LoginRequest, request: Request) -> TokenResponse:
    email = data.email.lower().strip()
    rate_limit(f"login:ip:{client_ip(request)}", 5, 15 * 60)
    rate_limit(f"login:email:{email}", 5, 15 * 60)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.hashed_password or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")
    if user.role in {UserRole.admin, UserRole.super_admin}:
        write_audit_log(db, action="auth.admin_login", entity_type="User", entity_id=user.id, user=user, request=request)
        db.commit()
    token_response = customer_token_response(user, db, request)
    db.commit()
    return token_response


def register_customer(db: Session, data: RegisterRequest) -> TokenResponse:
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
    response = customer_token_response(user, db)
    db.commit()
    return response


def request_otp_code(db: Session, data: OtpRequest, request: Request) -> dict:
    email = data.email.lower().strip()
    rate_limit(f"otp-request:ip:{client_ip(request)}", 10, 10 * 60)
    rate_limit(f"otp-request:email:{email}", 3, 10 * 60)
    code = f"{random.SystemRandom().randint(100000, 999999)}"
    db.add(
        AuthOtp(
            email=email,
            code_hash=hash_password(code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES),
        )
    )

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


def verify_otp_code(db: Session, data: OtpVerifyRequest, request: Request) -> TokenResponse:
    email = data.email.lower().strip()
    rate_limit(f"otp-verify:ip:{client_ip(request)}", 10, 10 * 60)
    rate_limit(f"otp-verify:email:{email}", 5, 10 * 60)
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
    response = customer_token_response(user, db, request)
    db.commit()
    return response


def reset_customer_password(db: Session, data: "PasswordResetRequest", request: Request) -> dict:
    from app.schemas.auth import PasswordResetRequest
    
    email = data.email.lower().strip()
    rate_limit(f"otp-verify:ip:{client_ip(request)}", 10, 10 * 60)
    rate_limit(f"otp-verify:email:{email}", 5, 10 * 60)
    
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        
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
        raise HTTPException(status_code=401, detail="Invalid or expired reset code")
    
    otp.used = True
    
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User account not found. Please register instead.")
        
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    
    return {"message": "Password successfully reset"}


def google_login_customer(db: Session, data: GoogleLoginRequest) -> TokenResponse:
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

            payload = id_token.verify_oauth2_token(data.credential, google_requests.Request(), settings.google_client_id)
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
    response = customer_token_response(user, db)
    db.commit()
    return response


def refresh_access_token(db: Session, refresh_token: str, request: Request | None = None) -> TokenResponse:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(refresh_token)))
    now = datetime.now(timezone.utc)
    if not stored or stored.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    expires_at = stored.expires_at if stored.expires_at.tzinfo else stored.expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    user = db.get(User, stored.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored.revoked_at = now
    new_raw = create_refresh_token(db, user, request)
    db.flush()
    replacement = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(new_raw)))
    if replacement:
        stored.replaced_by_token_id = replacement.id
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        role=user.role,
        name=user.name,
        email=user.email,
        refresh_token=new_raw,
    )


def revoke_refresh_token(db: Session, refresh_token: str) -> dict:
    stored = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(refresh_token)))
    if stored and stored.revoked_at is None:
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"message": "Refresh token revoked"}


def admin_status_payload(db: Session) -> dict:
    admin = db.scalar(select(User).where(User.email == DEFAULT_ADMIN_EMAIL))
    return {
        "exists": bool(admin),
        "email": admin.email if admin else None,
        "is_active": admin.is_active if admin else False,
        "default_password_ok": verify_password("Admin@12345", admin.hashed_password) if admin and admin.hashed_password else False,
    }


def ensure_admin_seed(db: Session) -> dict:
    if get_settings().app_env == "production":
        raise HTTPException(status_code=403, detail="Admin seeding endpoint is disabled in production")
    seed_database(db)
    seed_default_email_templates(db)
    return {"message": "Admin and seed data checked", **admin_status_payload(db)}
