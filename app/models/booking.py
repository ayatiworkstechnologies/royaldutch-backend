from datetime import date, time
from decimal import Decimal

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import BookingStatus
from app.models.mixins import TimestampMixin


class Booking(TimestampMixin, Base):
    __tablename__ = "bookings"
    __table_args__ = (Index("ix_bookings_staff_date_status", "staff_id", "booking_date", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_code: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), nullable=False, index=True)
    staff_id: Mapped[int | None] = mapped_column(ForeignKey("staff.id"), nullable=True, index=True)
    booking_date: Mapped[date] = mapped_column(nullable=False, index=True)
    booking_time: Mapped[time] = mapped_column(nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus),
        default=BookingStatus.pending,
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    first_visit: Mapped[bool] = mapped_column(default=True, nullable=False)

    patient = relationship("Patient", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    staff = relationship("Staff", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")


class BookingSlotLock(TimestampMixin, Base):
    __tablename__ = "booking_slot_locks"
    __table_args__ = (
        UniqueConstraint("staff_id", "booking_date", "booking_time", name="uq_booking_slot_lock"),
        Index("ix_booking_slot_locks_staff_date", "staff_id", "booking_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff.id"), nullable=False, index=True)
    booking_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    booking_time: Mapped[time] = mapped_column(Time, nullable=False)
    lock_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
