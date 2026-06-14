from datetime import datetime

from app.schemas.common import ORMModel, Timestamped


class WhatsAppSendRequest(ORMModel):
    recipient_phone: str
    message: str
    booking_id: int | None = None
    patient_id: int | None = None
    template: str | None = None


class WhatsAppMessageRead(Timestamped):
    id: int
    notification_id: int | None
    booking_id: int | None
    patient_id: int | None
    recipient_phone: str
    template: str | None
    message: str
    status: str
    provider: str | None
    provider_message_id: str | None
    error_message: str | None
    sent_at: datetime | None
