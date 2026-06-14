from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationUpdate
from app.services.audit_service import model_snapshot, write_audit_log
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(require_permission("notifications.manage"))])


@router.get("", response_model=None)
def list_notifications(db: DbSession, page: int | None = Query(default=None), limit: int | None = Query(default=None)):
    query = select(Notification).order_by(Notification.created_at.desc())
    if page is not None and limit is not None:
        return paginate_query(db, query, page, limit)
    return list(db.scalars(query).all())


@router.post("", response_model=NotificationRead)
def create_notification(data: NotificationCreate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Notification:
    notification = Notification(**data.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    write_audit_log(db, action="notification.create", entity_type="Notification", entity_id=notification.id, user=user, request=request, new_value=model_snapshot(notification))
    db.commit()
    return notification


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification(notification_id: int, data: NotificationUpdate, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    old_value = model_snapshot(notification)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(notification, field, value)
    db.commit()
    db.refresh(notification)
    write_audit_log(db, action="notification.update", entity_type="Notification", entity_id=notification.id, user=user, request=request, old_value=old_value, new_value=model_snapshot(notification))
    db.commit()
    return notification


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    old_value = model_snapshot(notification)
    db.delete(notification)
    write_audit_log(db, action="notification.delete", entity_type="Notification", entity_id=notification_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Notification deleted"}
