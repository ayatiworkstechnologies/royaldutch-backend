from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.core.permissions import require_permission
from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.models.user import User
from app.schemas.mail import MailMessageCreate, MailMessageRead, MailMessageUpdate
from app.services.mail_queue_service import claim_queued_mail, process_claimed_mail
from app.services.smtp_service import check_smtp_connection, send_mail_message
from app.services.audit_service import model_snapshot, write_audit_log
from app.utils.pagination import paginate_query

router = APIRouter(prefix="/mail", tags=["mail"], dependencies=[Depends(require_permission("mail.manage"))])


@router.get("", response_model=None)
def list_mail(db: DbSession, page: int | None = Query(default=None), limit: int | None = Query(default=None)):
    query = select(MailMessage).order_by(MailMessage.created_at.desc())
    if page is not None and limit is not None:
        result = paginate_query(db, query, page, limit)
        result["items"] = [MailMessageRead.model_validate(item).model_dump(mode="json") for item in result["items"]]
        return result
    return [MailMessageRead.model_validate(item).model_dump(mode="json") for item in db.scalars(query).all()]


@router.post("", response_model=MailMessageRead)
def create_mail(data: MailMessageCreate, db: DbSession) -> MailMessage:
    mail = MailMessage(**data.model_dump())
    db.add(mail)
    db.commit()
    db.refresh(mail)
    return mail


@router.get("/smtp-status")
def smtp_status() -> dict:
    return check_smtp_connection()


@router.post("/send-queued")
def send_queued_mail(
    db: DbSession,
    include_failed: bool = Query(default=False),
) -> dict:
    messages = claim_queued_mail(db, limit=100, include_failed=include_failed)
    sent = 0
    failed = 0
    results = []
    for mail in messages:
        process_claimed_mail(db, mail)
        if mail.status == MailStatus.sent:
            sent += 1
        elif mail.status == MailStatus.failed:
            failed += 1
        results.append({"id": mail.id, "status": mail.status, "error_message": mail.error_message})
    db.commit()
    return {"sent": sent, "failed": failed, "total": len(messages), "results": results}


@router.patch("/{mail_id}", response_model=MailMessageRead)
def update_mail(mail_id: int, data: MailMessageUpdate, db: DbSession) -> MailMessage:
    mail = db.get(MailMessage, mail_id)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail record not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(mail, field, value)
    db.commit()
    db.refresh(mail)
    return mail


@router.post("/{mail_id}/send", response_model=MailMessageRead)
def send_mail(mail_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> MailMessage:
    mail = db.get(MailMessage, mail_id)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail record not found")
    send_mail_message(mail)
    write_audit_log(db, action="mail.send", entity_type="MailMessage", entity_id=mail.id, user=user, request=request, new_value=model_snapshot(mail))
    db.commit()
    db.refresh(mail)
    return mail


@router.delete("/{mail_id}")
def delete_mail(mail_id: int, db: DbSession, request: Request, user: User = Depends(get_current_user)) -> dict:
    mail = db.get(MailMessage, mail_id)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail record not found")
    old_value = model_snapshot(mail)
    db.delete(mail)
    write_audit_log(db, action="mail.delete", entity_type="MailMessage", entity_id=mail_id, user=user, request=request, old_value=old_value)
    db.commit()
    return {"message": "Mail record deleted"}
