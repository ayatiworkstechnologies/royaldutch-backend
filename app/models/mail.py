from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import MailStatus
from app.models.mixins import TimestampMixin


class MailMessage(TimestampMixin, Base):
    __tablename__ = "mail_messages"

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
