from fastapi import APIRouter, Request, status

from app.api.deps import DbSession
from app.schemas.auth import GoogleLoginRequest, LoginRequest, OtpRequest, OtpVerifyRequest, RefreshTokenRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    admin_status_payload,
    ensure_admin_seed,
    google_login_customer,
    login_with_password,
    register_customer,
    refresh_access_token,
    request_otp_code,
    revoke_refresh_token,
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


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(data: RefreshTokenRequest, db: DbSession, request: Request) -> TokenResponse:
    return refresh_access_token(db, data.refresh_token, request)


@router.post("/logout")
def logout(data: RefreshTokenRequest, db: DbSession) -> dict:
    return revoke_refresh_token(db, data.refresh_token)


@router.get("/admin-status")
def admin_status(db: DbSession) -> dict:
    return admin_status_payload(db)


@router.post("/ensure-admin")
def ensure_admin(db: DbSession) -> dict:
    return ensure_admin_seed(db)
