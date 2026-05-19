from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Patient(TimestampMixin, Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str | None] = mapped_column(String(180), index=True)
    phone: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(30))
    age: Mapped[int | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000))
    documents: Mapped[str | None] = mapped_column(String(1000))

    bookings = relationship("Booking", back_populates="patient")
