from datetime import time

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Table, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RecordStatus
from app.models.mixins import TimestampMixin


staff_services = Table(
    "staff_services",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("staff_id", ForeignKey("staff.id"), nullable=False, index=True),
    Column("service_id", ForeignKey("services.id"), nullable=False, index=True),
    UniqueConstraint("staff_id", "service_id", name="uq_staff_service"),
)


class Staff(TimestampMixin, Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180), unique=True)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    specialization: Mapped[str | None] = mapped_column(String(180))
    profile_image: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus),
        default=RecordStatus.active,
        nullable=False,
    )

    services = relationship("Service", secondary=staff_services, back_populates="staff")
    availability = relationship("StaffAvailability", back_populates="staff", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="staff")


class StaffAvailability(TimestampMixin, Base):
    __tablename__ = "staff_availability"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    day_of_week: Mapped[int] = mapped_column(nullable=False)
    start_time: Mapped[time] = mapped_column(nullable=False)
    end_time: Mapped[time] = mapped_column(nullable=False)
    break_start_time: Mapped[time | None] = mapped_column(nullable=True)
    break_end_time: Mapped[time | None] = mapped_column(nullable=True)
    status: Mapped[RecordStatus] = mapped_column(
        Enum(RecordStatus),
        default=RecordStatus.active,
        nullable=False,
    )

    staff = relationship("Staff", back_populates="availability")
