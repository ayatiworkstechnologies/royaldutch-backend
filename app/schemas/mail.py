from app.models.enums import MailStatus
from app.schemas.common import ORMModel, Timestamped
from datetime import datetime


class MailMessageCreate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    invoice_id: int | None = None
    recipient_email: str
    cc_emails: str | None = None
    bcc_emails: str | None = None
    recipient_name: str | None = None
    subject: str
    body: str
    status: MailStatus = MailStatus.draft
    provider_message_id: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    last_attempt_at: datetime | None = None
    locked_at: datetime | None = None
    lock_token: str | None = None


class MailMessageUpdate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    invoice_id: int | None = None
    recipient_email: str | None = None
    cc_emails: str | None = None
    bcc_emails: str | None = None
    recipient_name: str | None = None
    subject: str | None = None
    body: str | None = None
    status: MailStatus | None = None
    provider_message_id: str | None = None
    error_message: str | None = None
    retry_count: int | None = None
    last_attempt_at: datetime | None = None
    locked_at: datetime | None = None
    lock_token: str | None = None


class MailMessageRead(MailMessageCreate, Timestamped):
    id: int
