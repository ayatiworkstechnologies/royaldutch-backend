from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.security import create_access_token, verify_password
from app.models.admin import AdminUser
from app.schemas.auth import LoginRequest, TokenResponse
from app.seed.clinic_data import seed_database
from app.services.email_template_service import seed_default_email_templates

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: DbSession) -> TokenResponse:
    admin = db.scalar(select(AdminUser).where(AdminUser.email == data.email))
    if not admin or not verify_password(data.password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(admin.id))


@router.get("/admin-status")
def admin_status(db: DbSession) -> dict:
    admin = db.scalar(select(AdminUser).where(AdminUser.email == "admin@clinicflow.local"))
    return {
        "exists": bool(admin),
        "email": admin.email if admin else None,
        "is_active": admin.is_active if admin else False,
        "default_password_ok": verify_password("Admin@12345", admin.hashed_password) if admin else False,
    }


@router.post("/ensure-admin")
def ensure_admin(db: DbSession) -> dict:
    seed_database(db)
    seed_default_email_templates(db)
    admin = db.scalar(select(AdminUser).where(AdminUser.email == "admin@clinicflow.local"))
    return {
        "message": "Admin and seed data checked",
        "exists": bool(admin),
        "default_password_ok": verify_password("Admin@12345", admin.hashed_password) if admin else False,
    }
