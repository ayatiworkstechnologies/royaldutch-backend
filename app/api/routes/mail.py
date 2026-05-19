from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.schemas.mail import MailMessageCreate, MailMessageRead, MailMessageUpdate
from app.services.smtp_service import send_mail_message

router = APIRouter(prefix="/mail", tags=["mail"], dependencies=[Depends(get_current_admin)])


@router.get("", response_model=list[MailMessageRead])
def list_mail(db: DbSession) -> list[MailMessage]:
    return list(db.scalars(select(MailMessage).order_by(MailMessage.created_at.desc())).all())


@router.post("", response_model=MailMessageRead)
def create_mail(data: MailMessageCreate, db: DbSession) -> MailMessage:
    mail = MailMessage(**data.model_dump())
    db.add(mail)
    db.commit()
    db.refresh(mail)
    return mail


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
def send_mail(mail_id: int, db: DbSession) -> MailMessage:
    mail = db.get(MailMessage, mail_id)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail record not found")
    send_mail_message(mail)
    db.commit()
    db.refresh(mail)
    return mail


@router.post("/send-queued")
def send_queued_mail(db: DbSession) -> dict:
    messages = db.scalars(select(MailMessage).where(MailMessage.status == MailStatus.queued)).all()
    sent = 0
    failed = 0
    for mail in messages:
        send_mail_message(mail)
        if mail.status == MailStatus.sent:
            sent += 1
        elif mail.status == MailStatus.failed:
            failed += 1
    db.commit()
    return {"sent": sent, "failed": failed, "total": len(messages)}


@router.delete("/{mail_id}")
def delete_mail(mail_id: int, db: DbSession) -> dict:
    mail = db.get(MailMessage, mail_id)
    if not mail:
        raise HTTPException(status_code=404, detail="Mail record not found")
    db.delete(mail)
    db.commit()
    return {"message": "Mail record deleted"}
