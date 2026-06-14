from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.enums import UserRole
from app.models.user import User


ROLE_PERMISSIONS = {
    UserRole.super_admin: {"*"},
    UserRole.admin: {"*"},
    UserRole.receptionist: {
        "bookings.read",
        "bookings.manage",
        "patients.read",
        "patients.manage",
        "mail.manage",
        "notifications.manage",
        "dashboard.read",
        "reports.read",
    },
    UserRole.doctor: {"bookings.read", "patients.read", "dashboard.read", "reports.read"},
    UserRole.accountant: {"billing.manage", "payments.manage", "patients.read", "dashboard.read", "reports.read"},
    UserRole.marketing: {"mail.manage", "email_templates.manage", "notifications.manage", "dashboard.read", "reports.read"},
    UserRole.customer: {"account.read", "account.update"},
}


def has_permission(user: User, permission: str) -> bool:
    try:
        role = UserRole(user.role)
    except ValueError:
        return False
    permissions = ROLE_PERMISSIONS.get(role, set())
    return "*" in permissions or permission in permissions


def require_permission(permission: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
        return user

    return dependency


def require_super_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")
    return user
