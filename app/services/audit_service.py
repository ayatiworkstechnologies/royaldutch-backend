from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User


def request_ip(request: Request | None) -> str | None:
    if not request:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def write_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    user: User | None = None,
    request: Request | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user.id if user else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        old_value=old_value,
        new_value=new_value,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent") if request else None,
        request_id=getattr(request.state, "request_id", None) if request else None,
    )
    db.add(log)
    return log


def model_snapshot(obj) -> dict:
    def clean(value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    return {
        column.name: clean(getattr(obj, column.name))
        for column in obj.__table__.columns
        if column.name not in {"hashed_password"}
    }
