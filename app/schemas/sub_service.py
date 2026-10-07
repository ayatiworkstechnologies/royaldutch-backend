from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, Field, StringConstraints, model_validator

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=220)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]

def normalize_price(value: Any) -> str:
    """Normalize an exact price or a `minimum-maximum` price range."""
    if len(str(value)) > 50:
        raise ValueError("price must be at most 50 characters")
    if isinstance(value, str):
        normalized = value.replace(",", "")
        for dash in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"):
            normalized = normalized.replace(dash, "-")
        parts = [part.strip() for part in normalized.split("-")]
    else:
        parts = [str(value)]
    if len(parts) not in (1, 2) or any(not part for part in parts):
        raise ValueError("price must be a non-negative amount or range such as 200-500")
    try:
        amounts = [Decimal(part) for part in parts]
    except Exception as exc:
        raise ValueError("price must be a non-negative amount or range such as 200-500") from exc
    if any(amount < 0 or not amount.is_finite() for amount in amounts):
        raise ValueError("price must contain non-negative finite amounts")
    if any(-amount.as_tuple().exponent > 2 or len(amount.as_tuple().digits) > 10 for amount in amounts):
        raise ValueError("price amounts may have at most 10 digits and 2 decimal places")
    if len(amounts) == 2 and amounts[0] > amounts[1]:
        raise ValueError("price range minimum cannot exceed maximum")

    def display(amount: Decimal) -> str:
        return format(amount, "f")

    if len(amounts) == 1:
        return f"{amounts[0]:.2f}"
    return "-".join(display(amount) for amount in amounts)


Price = Annotated[str, BeforeValidator(normalize_price)]


class SubServiceCreate(ORMModel):
    name: Name
    slug: Slug
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: Price | None = None
    currency: Currency = "AED"
    image: str | None = Field(default=None, max_length=500)
    status: RecordStatus = RecordStatus.active


class SubServiceUpdate(ORMModel):
    name: Name | None = None
    slug: Slug | None = None
    description: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: Price | None = None
    currency: Currency | None = None
    image: str | None = Field(default=None, max_length=500)
    status: RecordStatus | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("name", "slug", "currency", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class SubServiceRead(SubServiceCreate, Timestamped):
    id: int
    service_id: int
    service_name: str | None = None
