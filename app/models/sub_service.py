from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


class SubService(TimestampMixin, Base):
    __tablename__ = "sub_services"
    __table_args__ = (UniqueConstraint("service_id", "slug", name="uq_sub_service_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(220))
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int | None]
    # A string supports both exact prices ("200") and ranges ("200-500").
    price: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(10), default="AED")
    image: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.active)

    service = relationship("Service", back_populates="sub_services")

    @property
    def service_name(self) -> str | None:
        return self.service.name if self.service else None
