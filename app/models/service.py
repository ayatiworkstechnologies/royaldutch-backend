from decimal import Decimal

from sqlalchemy import event, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.catalog_sequence import assign_catalog_number
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


class Service(TimestampMixin, Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    display_id: Mapped[int] = mapped_column(unique=True, nullable=False)
    external_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    image: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus),
        default=RecordStatus.active,
        nullable=False,
    )

    category = relationship("Category", back_populates="services")
    staff = relationship("Staff", secondary="staff_services", back_populates="services")
    bookings = relationship("Booking", back_populates="service")
    sub_services = relationship("SubService", back_populates="service", cascade="all, delete-orphan")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None


event.listen(Service, "before_insert", assign_catalog_number)
