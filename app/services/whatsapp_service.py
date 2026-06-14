from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notification import Notification
from app.models.whatsapp import WhatsAppMessage
from app.schemas.whatsapp import WhatsAppSendRequest


def create_whatsapp_message(db: Session, data: WhatsAppSendRequest, notification_id: int | None = None) -> WhatsAppMessage:
    settings = get_settings()
    message = WhatsAppMessage(
        notification_id=notification_id,
        booking_id=data.booking_id,
        patient_id=data.patient_id,
        recipient_phone=data.recipient_phone,
        template=data.template,
        message=data.message,
        status="queued",
        provider=settings.whatsapp_provider,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def send_whatsapp_message(db: Session, message: WhatsAppMessage) -> WhatsAppMessage:
    settings = get_settings()
    if not message.recipient_phone:
        message.status = "failed"
        message.error_message = "Recipient phone is required"
    elif settings.whatsapp_provider == "noop":
        message.status = "sent"
        message.provider_message_id = f"noop-{uuid4().hex}"
        message.sent_at = datetime.now(timezone.utc)
    elif not settings.whatsapp_api_url or not settings.whatsapp_api_token:
        message.status = "failed"
        message.error_message = "WhatsApp provider is not configured"
    else:
        message.status = "queued"
        message.error_message = "External WhatsApp delivery client is not enabled in this build"
    db.commit()
    db.refresh(message)
    return message


def send_notification_whatsapp(db: Session, notification_id: int) -> WhatsAppMessage:
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.channel != NotificationChannel.whatsapp:
        raise HTTPException(status_code=400, detail="Notification channel is not whatsapp")
    message = create_whatsapp_message(
        db,
        WhatsAppSendRequest(
            recipient_phone=notification.recipient,
            message=notification.message,
            booking_id=notification.booking_id,
        ),
        notification_id=notification.id,
    )
    sent = send_whatsapp_message(db, message)
    notification.status = NotificationStatus.sent if sent.status == "sent" else NotificationStatus.failed
    db.commit()
    return sent
