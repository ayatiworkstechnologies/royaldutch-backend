from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings


def origin_is_allowed(origin: str, settings: Settings) -> bool:
    explicit_origins = set(settings.cors_origins)
    if origin in explicit_origins:
        return True
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return True
    if origin.endswith(".vercel.app") and origin.startswith("https://"):
        return True
    if origin.endswith(".onrender.com") and origin.startswith("https://"):
        return True
    return False


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("origin", "")

        if request.method == "OPTIONS" and origin and origin_is_allowed(origin, self.settings):
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        if origin and origin_is_allowed(origin, self.settings):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = request.headers.get(
                "access-control-request-headers",
                "Authorization,Content-Type",
            )
            response.headers["Vary"] = "Origin"

        return response
