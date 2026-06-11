from datetime import date
from decimal import Decimal

from pydantic import Field

from app.models.enums import InvoiceStatus
from app.schemas.common import ORMModel, Timestamped


class InvoiceItemCreate(ORMModel):
    description: str
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = Field(ge=0)


class InvoiceItemRead(InvoiceItemCreate, Timestamped):
    id: int
    invoice_id: int
    line_total: Decimal


class InvoiceCreate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    issue_date: date
    due_date: date | None = None
    discount_amount: Decimal = Field(default=0, ge=0)
    tax_amount: Decimal = Field(default=0, ge=0)
    paid_amount: Decimal = Field(default=0, ge=0)
    currency: str = "AED"
    status: InvoiceStatus = InvoiceStatus.draft
    notes: str | None = None
    items: list[InvoiceItemCreate] = Field(min_length=1)


class InvoiceFromBookingCreate(ORMModel):
    due_date: date | None = None
    discount_amount: Decimal = Field(default=0, ge=0)
    tax_amount: Decimal = Field(default=0, ge=0)
    notes: str | None = None


class InvoiceUpdate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    discount_amount: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    paid_amount: Decimal | None = Field(default=None, ge=0)
    currency: str | None = None
    status: InvoiceStatus | None = None
    notes: str | None = None
    items: list[InvoiceItemCreate] | None = Field(default=None, min_length=1)


class InvoiceRead(Timestamped):
    id: int
    invoice_number: str
    booking_id: int | None
    patient_id: int | None
    issue_date: date
    due_date: date | None
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    currency: str
    status: InvoiceStatus
    notes: str | None
    items: list[InvoiceItemRead] = Field(default_factory=list)
