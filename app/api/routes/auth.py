from fastapi import APIRouter, Request, status

from app.api.deps import DbSession
from app.schemas.auth import GoogleLoginRequest, LoginRequest, OtpRequest, OtpVerifyRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    admin_status_payload,
    ensure_admin_seed,
    google_login_customer,
    login_with_password,
    register_customer,
    request_otp_code,
    verify_otp_code,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
    return login_with_password(db, data, request)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> TokenResponse:
    return register_customer(db, data)


@router.post("/otp/request")
def request_otp(data: OtpRequest, db: DbSession, request: Request) -> dict:
    return request_otp_code(db, data, request)


@router.post("/otp/verify", response_model=TokenResponse)
def verify_otp(data: OtpVerifyRequest, db: DbSession, request: Request) -> TokenResponse:
    return verify_otp_code(db, data, request)


@router.post("/google", response_model=TokenResponse)
def google_login(data: GoogleLoginRequest, db: DbSession) -> TokenResponse:
    return google_login_customer(db, data)


@router.get("/admin-status")
def admin_status(db: DbSession) -> dict:
    return admin_status_payload(db)


@router.post("/ensure-admin")
def ensure_admin(db: DbSession) -> dict:
    return ensure_admin_seed(db)
