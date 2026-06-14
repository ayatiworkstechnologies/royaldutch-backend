from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.enums import MailStatus
from app.models.mail import MailMessage
from app.services.smtp_service import send_mail_message

MAX_MAIL_RETRIES = 3
STALE_LOCK_MINUTES = 15


def claim_queued_mail(db: Session, limit: int = 10, include_failed: bool = False) -> list[MailMessage]:
    statuses = [MailStatus.queued]
    if include_failed:
        statuses.append(MailStatus.failed)
    now = datetime.now(timezone.utc)
    token = uuid4().hex

    candidate_ids = [
        row[0]
        for row in db.execute(
            select(MailMessage.id)
            .where(MailMessage.status.in_(statuses), MailMessage.retry_count < MAX_MAIL_RETRIES)
            .order_by(MailMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        ).all()
    ]
    if not candidate_ids:
        return []

    db.execute(
        update(MailMessage)
        .where(
            MailMessage.id.in_(candidate_ids),
            MailMessage.status.in_(statuses),
            MailMessage.retry_count < MAX_MAIL_RETRIES,
        )
        .values(status=MailStatus.processing, locked_at=now, lock_token=token)
    )
    db.commit()
    return list(db.scalars(select(MailMessage).where(MailMessage.lock_token == token)).all())


def process_claimed_mail(db: Session, mail: MailMessage, attachments=None) -> MailMessage:
    mail.retry_count += 1
    mail.last_attempt_at = datetime.now(timezone.utc)
    send_mail_message(mail, attachments=attachments)
    mail.locked_at = None
    mail.lock_token = None
    db.add(mail)
    return mail


def recover_stale_processing_mail(db: Session, stale_minutes: int = STALE_LOCK_MINUTES) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_minutes)
    result = db.execute(
        update(MailMessage)
        .where(
            MailMessage.status == MailStatus.processing,
            MailMessage.locked_at.is_not(None),
            MailMessage.locked_at < cutoff,
            MailMessage.retry_count < MAX_MAIL_RETRIES,
        )
        .values(status=MailStatus.queued, locked_at=None, lock_token=None)
    )
    db.commit()
    return result.rowcount or 0
