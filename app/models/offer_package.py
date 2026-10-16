from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


class OfferPackage(TimestampMixin, Base):
    __tablename__ = "offer_packages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    original_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    offer_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    status: Mapped[RecordStatus] = mapped_column(Enum(RecordStatus), default=RecordStatus.active, nullable=False)

    service = relationship("Service", back_populates="offer_packages")
    bookings = relationship("Booking", back_populates="offer_package")

    @property
    def discount_percentage(self) -> int:
        if not self.original_price:
            return 0
        return round((self.original_price - self.offer_price) * 100 / self.original_price)

    @property
    def service_name(self) -> str | None:
        return self.service.name if self.service else None

    @property
    def category_id(self) -> int | None:
        return self.service.category_id if self.service else None
