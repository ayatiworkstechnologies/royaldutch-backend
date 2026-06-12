from datetime import date
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import InvoiceStatus
from app.models.mixins import TimestampMixin


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"), nullable=True, index=True)
    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"), nullable=True, index=True)
    issue_date: Mapped[date] = mapped_column(nullable=False)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="AED", nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.draft, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", foreign_keys="Payment.invoice_id")
    booking = relationship("Booking")
    patient = relationship("Patient")


class InvoiceItem(TimestampMixin, Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
