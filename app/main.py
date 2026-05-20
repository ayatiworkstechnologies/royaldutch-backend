from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.cors import DynamicCORSMiddleware
from app.db.base import Base
from app.db.session import engine
from app.db.session import SessionLocal
from app.services.email_template_service import seed_default_email_templates

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(DynamicCORSMiddleware, settings=settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def create_tables() -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_default_email_templates(db)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
