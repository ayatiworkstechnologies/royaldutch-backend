from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


class EmailTemplate(TimestampMixin, Base):
    __tablename__ = "email_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str] = mapped_column(String(220), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.active, nullable=False)
