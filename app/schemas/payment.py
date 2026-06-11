from decimal import Decimal

from pydantic import Field

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.common import ORMModel, Timestamped


class PaymentCreate(ORMModel):
    booking_id: int | None = None
    invoice_id: int | None = None
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod = PaymentMethod.pay_at_clinic
    payment_status: PaymentStatus = PaymentStatus.unpaid
    transaction_id: str | None = None


class PaymentUpdate(ORMModel):
    booking_id: int | None = None
    invoice_id: int | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    transaction_id: str | None = None


class PaymentRead(PaymentCreate, Timestamped):
    id: int
