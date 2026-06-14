from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.permissions import require_super_admin
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogRead
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/audit-logs", tags=["audit logs"], dependencies=[Depends(require_super_admin)])


@router.get("", response_model=None)
def list_audit_logs(
    db: DbSession,
    page: int | None = Query(default=None),
    limit: int | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
):
    query = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if page is not None and limit is not None:
        result = paginate_query(db, query, page, limit)
        result["items"] = [AuditLogRead.model_validate(item).model_dump(mode="json") for item in result["items"]]
        return result
    return [AuditLogRead.model_validate(item).model_dump(mode="json") for item in db.scalars(query).all()]
