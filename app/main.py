from fastapi import FastAPI
import asyncio

from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import add_cors_middleware
from app.db.base import Base
from app.db.session import engine
from app.db.session import SessionLocal
from app.seed.clinic_data import seed_database
from app.services.email_template_service import seed_default_email_templates
from app.services.settings_service import seed_clinic_settings
from app.models.mail import MailMessage
from app.models.enums import MailStatus
from app.services.smtp_service import send_mail_message
from sqlalchemy import select

settings = get_settings()


async def process_mail_queue():
    while True:
        try:
            with SessionLocal() as db:
                messages = db.scalars(select(MailMessage).where(MailMessage.status == MailStatus.queued).limit(10)).all()
                if messages:
                    for mail in messages:
                        send_mail_message(mail)
                    db.commit()
        except Exception as e:
            print(f"Mail worker error: {e}")
        await asyncio.sleep(10)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    add_cors_middleware(app, settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_clinic_settings(db)
            seed_database(db)
            seed_default_email_templates(db)
        
        # Start mail background worker
        asyncio.create_task(process_mail_queue())

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
