from datetime import date
from decimal import Decimal

from app.models.enums import InvoiceStatus
from app.schemas.common import ORMModel, Timestamped


class InvoiceItemCreate(ORMModel):
    description: str
    quantity: int = 1
    unit_price: Decimal


class InvoiceItemRead(InvoiceItemCreate, Timestamped):
    id: int
    invoice_id: int
    line_total: Decimal


class InvoiceCreate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    issue_date: date
    due_date: date | None = None
    discount_amount: Decimal = 0
    tax_amount: Decimal = 0
    paid_amount: Decimal = 0
    currency: str = "AED"
    status: InvoiceStatus = InvoiceStatus.draft
    notes: str | None = None
    items: list[InvoiceItemCreate]


class InvoiceFromBookingCreate(ORMModel):
    due_date: date | None = None
    discount_amount: Decimal = 0
    tax_amount: Decimal = 0
    notes: str | None = None


class InvoiceUpdate(ORMModel):
    booking_id: int | None = None
    patient_id: int | None = None
    issue_date: date | None = None
    due_date: date | None = None
    discount_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    paid_amount: Decimal | None = None
    currency: str | None = None
    status: InvoiceStatus | None = None
    notes: str | None = None
    items: list[InvoiceItemCreate] | None = None


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
    items: list[InvoiceItemRead] = []
