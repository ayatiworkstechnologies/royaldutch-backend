from fastapi import APIRouter, Depends, Request

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.user import User
from app.models.whatsapp import WhatsAppMessage
from app.schemas.whatsapp import WhatsAppMessageRead, WhatsAppSendRequest
from app.services.audit_service import model_snapshot, write_audit_log
from app.services.whatsapp_service import create_whatsapp_message, send_notification_whatsapp, send_whatsapp_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"], dependencies=[Depends(require_permission("notifications.manage"))])


@router.post("/send", response_model=WhatsAppMessageRead)
def send_whatsapp(data: WhatsAppSendRequest, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> WhatsAppMessage:
    message = create_whatsapp_message(db, data)
    message = send_whatsapp_message(db, message)
    write_audit_log(db, action="whatsapp.send", entity_type="WhatsAppMessage", entity_id=message.id, user=user, request=request, new_value=model_snapshot(message))
    db.commit()
    return message


@router.post("/notifications/{notification_id}/send", response_model=WhatsAppMessageRead)
def send_notification(notification_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> WhatsAppMessage:
    message = send_notification_whatsapp(db, notification_id)
    write_audit_log(db, action="whatsapp.notification_send", entity_type="WhatsAppMessage", entity_id=message.id, user=user, request=request, new_value=model_snapshot(message))
    db.commit()
    return message
