from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=220)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]
Price = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


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
