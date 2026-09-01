from fastapi import APIRouter

from app.api.routes import (
    account,
    admin_users,
    audit_logs,
    auth,
    billing,
    bookings,
    categories,
    chat,
    contacts,
    dashboard,
    email_templates,
    mail,
    notifications,
    patients,
    patient_documents,
    payments,
    prescriptions,
    reports,
    services,
    settings,
    staff,
    staff_dashboard,
    whatsapp,
)

api_router = APIRouter()
api_router.include_router(account.router)
api_router.include_router(admin_users.router)
api_router.include_router(contacts.router)
api_router.include_router(audit_logs.router)
api_router.include_router(auth.router)
api_router.include_router(chat.router)
api_router.include_router(categories.router)
api_router.include_router(services.router)
api_router.include_router(settings.router)
api_router.include_router(staff.router)
api_router.include_router(bookings.router)
api_router.include_router(patients.router)
api_router.include_router(patient_documents.router)
api_router.include_router(payments.router)
api_router.include_router(prescriptions.router)
api_router.include_router(reports.router)
api_router.include_router(billing.router)
api_router.include_router(mail.router)
api_router.include_router(email_templates.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
api_router.include_router(staff_dashboard.router)
api_router.include_router(whatsapp.router)
