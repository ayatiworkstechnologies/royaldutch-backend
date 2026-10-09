from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped
from app.schemas.sub_service import Price

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]
Slug = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=220)]
Currency = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10)]


class ServicePackageCreate(ORMModel):
    name: Name
    slug: Slug
    description: str | None = None
    sessions: int | None = Field(default=None, gt=0)
    price: Price | None = None
    currency: Currency = "AED"
    status: RecordStatus = RecordStatus.active


class ServicePackageUpdate(ORMModel):
    name: Name | None = None
    slug: Slug | None = None
    description: str | None = None
    sessions: int | None = Field(default=None, gt=0)
    price: Price | None = None
    currency: Currency | None = None
    status: RecordStatus | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("name", "slug", "currency", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class ServicePackageRead(ServicePackageCreate, Timestamped):
    id: int
    sub_service_id: int
    sub_service_name: str | None = None
