from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


_buckets: dict[str, deque[float]] = defaultdict(deque)
_redis_client = None


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(key: str, limit: int, window_seconds: int) -> None:
    settings = get_settings()
    if settings.redis_url:
        try:
            redis = redis_client(settings.redis_url)
            count = redis.incr(f"rate-limit:{key}")
            if count == 1:
                redis.expire(f"rate-limit:{key}", window_seconds)
            if count > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                )
            return
        except HTTPException:
            raise
        except Exception:
            if settings.app_env == "production":
                raise HTTPException(status_code=503, detail="Rate limiter is unavailable")

    now = monotonic()
    bucket = _buckets[key]
    while bucket and now - bucket[0] >= window_seconds:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    bucket.append(now)


def clear_rate_limits() -> None:
    _buckets.clear()


def redis_client(redis_url: str):
    global _redis_client
    if _redis_client is None:
        from redis import Redis

        _redis_client = Redis.from_url(redis_url, decode_responses=True)
    return _redis_client
