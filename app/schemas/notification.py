from app.models.enums import NotificationChannel, NotificationStatus
from app.schemas.common import ORMModel, Timestamped


class NotificationCreate(ORMModel):
    booking_id: int | None = None
    channel: NotificationChannel
    recipient: str
    subject: str | None = None
    message: str
    status: NotificationStatus = NotificationStatus.queued


class NotificationUpdate(ORMModel):
    status: NotificationStatus | None = None
    subject: str | None = None
    message: str | None = None


class NotificationRead(NotificationCreate, Timestamped):
    id: int
