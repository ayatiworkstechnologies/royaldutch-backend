from decimal import Decimal
from typing import Annotated, Any

from pydantic import BeforeValidator, Field

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


def normalize_optional_price(value: Any) -> Any:
    """Treat an empty form field as no price and normalize digit grouping."""
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None
        return value.replace(",", "")
    return value


OptionalPrice = Annotated[Decimal | None, BeforeValidator(normalize_optional_price)]


class ServiceBase(ORMModel):
    external_id: int | None = None
    category_id: int
    name: str
    slug: str
    description: str | None = None
    duration_minutes: int | None = None
    price: OptionalPrice = None
    currency: str = "AED"
    image: str | None = None
    status: RecordStatus = RecordStatus.active


class ServiceCreate(ServiceBase):
    staff_ids: list[int] = Field(default_factory=list)


class ServiceUpdate(ORMModel):
    external_id: int | None = None
    category_id: int | None = None
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    price: OptionalPrice = None
    currency: str | None = None
    image: str | None = None
    status: RecordStatus | None = None
    staff_ids: list[int] | None = None


class ServiceRead(ServiceBase, Timestamped):
    id: int
    display_id: int
    category_name: str | None = None


class ServiceWithCategory(ServiceRead):
    category_name: str | None = None
