from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import MailStatus
from app.models.mixins import TimestampMixin


class MailMessage(TimestampMixin, Base):
    __tablename__ = "mail_messages"
    __table_args__ = (
        Index("ix_mail_queue_scan", "status", "retry_count", "created_at", "locked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoices.id"), nullable=True, index=True)
    recipient_email: Mapped[str] = mapped_column(String(180), nullable=False)
    cc_emails: Mapped[str | None] = mapped_column(String(1000))
    bcc_emails: Mapped[str | None] = mapped_column(String(1000))
    recipient_name: Mapped[str | None] = mapped_column(String(180))
    subject: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MailStatus] = mapped_column(Enum(MailStatus), default=MailStatus.draft, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(220))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lock_token: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
