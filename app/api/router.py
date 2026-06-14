from fastapi import APIRouter

from app.api.routes import (
    account,
    audit_logs,
    auth,
    billing,
    bookings,
    categories,
    dashboard,
    email_templates,
    mail,
    notifications,
    patients,
    payments,
    services,
    settings,
    staff,
)

api_router = APIRouter()
api_router.include_router(account.router)
api_router.include_router(audit_logs.router)
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(services.router)
api_router.include_router(settings.router)
api_router.include_router(staff.router)
api_router.include_router(bookings.router)
api_router.include_router(patients.router)
api_router.include_router(payments.router)
api_router.include_router(billing.router)
api_router.include_router(mail.router)
api_router.include_router(email_templates.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
