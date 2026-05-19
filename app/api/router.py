from fastapi import APIRouter

from app.api.routes import auth, billing, bookings, categories, dashboard, mail, notifications, patients, payments, services, staff

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(categories.router)
api_router.include_router(services.router)
api_router.include_router(staff.router)
api_router.include_router(bookings.router)
api_router.include_router(patients.router)
api_router.include_router(payments.router)
api_router.include_router(billing.router)
api_router.include_router(mail.router)
api_router.include_router(notifications.router)
api_router.include_router(dashboard.router)
