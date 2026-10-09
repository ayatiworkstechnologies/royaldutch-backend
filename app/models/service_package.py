from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


class ServicePackage(TimestampMixin, Base):
    """A sellable package belonging to one sub-service."""

    __tablename__ = "service_packages"
    __table_args__ = (UniqueConstraint("sub_service_id", "slug", name="uq_service_package_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sub_service_id: Mapped[int] = mapped_column(ForeignKey("sub_services.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    slug: Mapped[str] = mapped_column(String(220))
    description: Mapped[str | None] = mapped_column(Text)
    sessions: Mapped[int | None]
    price: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str] = mapped_column(String(10), default="AED")
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.active)

    sub_service = relationship("SubService", back_populates="packages")

    @property
    def sub_service_name(self) -> str | None:
        return self.sub_service.name if self.sub_service else None
