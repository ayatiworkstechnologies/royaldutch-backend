from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.enums import UserRole
from app.models.user import User


ROLE_PERMISSIONS = {
    # super_admin — full access (Admin in UI)
    UserRole.super_admin: {"*"},

    # admin — all operational access, view + update (Manager in UI)
    UserRole.admin: {
        "dashboard.read",
        "reports.read",
        "bookings.read", "bookings.manage",
        "patients.read", "patients.manage",
        "categories.read", "categories.manage",
        "services.read", "services.manage",
        "staff.read", "staff.manage",
        "billing.read", "billing.manage",
        "payments.read", "payments.manage",
        "mail.read", "mail.manage",
        "email_templates.read", "email_templates.manage",
        "notifications.read", "notifications.manage",
        "settings.read", "settings.manage",
        "audit_logs.read",
    },

    # receptionist — booking workflow + billing + payments (Receptionist in UI)
    UserRole.receptionist: {
        "dashboard.read",
        "bookings.read", "bookings.manage",
        "patients.read", "patients.manage",
        "billing.read", "billing.manage",
        "payments.read", "payments.manage",
        "notifications.manage",
    },

    UserRole.doctor:           {"bookings.read", "bookings.manage", "patients.read", "dashboard.read", "reports.read"},
    UserRole.nurse:            {"bookings.read", "bookings.manage", "patients.read", "dashboard.read"},
    UserRole.physiotherapist:  {"bookings.read", "bookings.manage", "patients.read", "dashboard.read"},
    UserRole.dentist:          {"bookings.read", "bookings.manage", "patients.read", "dashboard.read"},
    UserRole.laser_specialist: {"bookings.read", "bookings.manage", "patients.read", "dashboard.read"},
    UserRole.facial_therapist: {"bookings.read", "bookings.manage", "patients.read", "dashboard.read"},
    UserRole.accountant: {"billing.manage", "billing.read", "payments.manage", "payments.read", "patients.read", "dashboard.read", "reports.read"},
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
