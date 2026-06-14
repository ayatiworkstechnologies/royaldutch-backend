from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin_user import AdminUserCreate, AdminUserUpdate

ADMIN_MANAGED_ROLES = {UserRole.super_admin, UserRole.admin, UserRole.receptionist, UserRole.doctor, UserRole.accountant, UserRole.marketing}


def validate_admin_role(role: str) -> None:
    if role not in {item.value for item in ADMIN_MANAGED_ROLES}:
        raise HTTPException(status_code=400, detail="Unsupported admin user role")


def create_admin_user(db: Session, data: AdminUserCreate) -> User:
    email = data.email.lower().strip()
    validate_admin_role(data.role)
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=400, detail="User with this email already exists")
    user = User(
        name=data.name.strip(),
        email=email,
        hashed_password=hash_password(data.password) if data.password else None,
        role=data.role,
        is_active=data.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(db: Session, user: User, data: AdminUserUpdate) -> User:
    update_data = data.model_dump(exclude_unset=True)
    if "role" in update_data and update_data["role"] is not None:
        validate_admin_role(update_data["role"])
    if "email" in update_data and update_data["email"]:
        update_data["email"] = update_data["email"].lower().strip()
        existing = db.scalar(select(User).where(User.email == update_data["email"], User.id != user.id))
        if existing:
            raise HTTPException(status_code=400, detail="User with this email already exists")
    password = update_data.pop("password", None)
    for field, value in update_data.items():
        setattr(user, field, value)
    if password:
        user.hashed_password = hash_password(password)
    db.commit()
    db.refresh(user)
    return user
