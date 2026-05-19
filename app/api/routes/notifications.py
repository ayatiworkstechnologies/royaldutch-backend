from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationUpdate

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[NotificationRead])
def list_notifications(db: DbSession) -> list[Notification]:
    return list(db.scalars(select(Notification).order_by(Notification.created_at.desc())).all())


@router.post("", response_model=NotificationRead)
def create_notification(data: NotificationCreate, db: DbSession) -> Notification:
    notification = Notification(**data.model_dump())
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}", response_model=NotificationRead)
def update_notification(notification_id: int, data: NotificationUpdate, db: DbSession) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(notification, field, value)
    db.commit()
    db.refresh(notification)
    return notification
