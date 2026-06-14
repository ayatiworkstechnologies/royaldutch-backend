import contextvars
import json
import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, Request

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
logger = logging.getLogger("royaldutch.api")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None) or request_id_context.get(),
        }
        for key in ("method", "path", "status_code", "duration_ms", "user_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    if logger.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def add_request_logging_middleware(app: FastAPI) -> None:
    configure_logging()

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            status_code = response.status_code if response else 500
            if response:
                response.headers["X-Request-ID"] = request_id
            user_id = getattr(getattr(request, "state", None), "user_id", None)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "request_complete",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(elapsed_ms, 2),
                    "user_id": user_id,
                },
            )
            request_id_context.reset(token)
