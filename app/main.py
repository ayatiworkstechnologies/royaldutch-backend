import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import add_cors_middleware
from app.core.logging import add_request_logging_middleware
from app.db.base import Base
from app.db.session import engine
from app.db.session import SessionLocal
from app.seed.clinic_data import seed_database
from app.services.email_template_service import seed_default_email_templates
from app.services.settings_service import seed_clinic_settings
from app.services.mail_queue_service import claim_queued_mail, process_claimed_mail, recover_stale_processing_mail
from starlette.middleware.trustedhost import TrustedHostMiddleware

mail_worker_task: asyncio.Task | None = None


async def process_mail_queue():
    while True:
        try:
            with SessionLocal() as db:
                recover_stale_processing_mail(db)
                messages = claim_queued_mail(db, limit=10, include_failed=True)
                if messages:
                    for mail in messages:
                        process_claimed_mail(db, mail)
                    db.commit()
        except Exception as e:
            print(f"Mail worker error: {e}")
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mail_worker_task
    settings = get_settings()
    if settings.app_env != "production":
        Base.metadata.create_all(bind=engine)
    if settings.run_startup_seeders and settings.app_env != "production":
        with SessionLocal() as db:
            seed_clinic_settings(db)
            seed_database(db)
            seed_default_email_templates(db)

    if settings.app_env != "production" or settings.enable_in_process_worker:
        mail_worker_task = asyncio.create_task(process_mail_queue())

    try:
        yield
    finally:
        if mail_worker_task:
            mail_worker_task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_production_safety()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    add_cors_middleware(app, settings)
    add_request_logging_middleware(app)
    if settings.trusted_host_list:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_host_list)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
