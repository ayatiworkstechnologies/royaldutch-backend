from decimal import Decimal

from pydantic import Field

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


class ServiceBase(ORMModel):
    external_id: int | None = None
    category_id: int
    name: str
    slug: str
    description: str | None = None
    duration_minutes: int | None = None
    price: Decimal | None = None
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
    price: Decimal | None = None
    currency: str | None = None
    image: str | None = None
    status: RecordStatus | None = None
    staff_ids: list[int] | None = None


class ServiceRead(ServiceBase, Timestamped):
    id: int


class ServiceWithCategory(ServiceRead):
    category_name: str | None = None
