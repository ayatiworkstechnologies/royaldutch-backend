from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class WhatsAppMessage(TimestampMixin, Base):
    __tablename__ = "whatsapp_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    notification_id: Mapped[int | None] = mapped_column(ForeignKey("notifications.id"), nullable=True, index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    recipient_phone: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    template: Mapped[str | None] = mapped_column(String(120), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(220), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
