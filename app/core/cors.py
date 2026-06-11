"""CORS configuration using FastAPI's built-in CORSMiddleware."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import Settings


def add_cors_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach CORSMiddleware to the FastAPI application."""
    origins = settings.cors_origins or []
    # Always include localhost origins for development
    for port in ("3000", "3001", "5173", "8000"):
        for host in ("http://localhost", "http://127.0.0.1"):
            origin = f"{host}:{port}"
            if origin not in origins:
                origins.append(origin)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=settings.backend_cors_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
