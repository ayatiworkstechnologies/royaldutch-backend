from decimal import Decimal
from typing import Annotated

from pydantic import Field, StringConstraints, model_validator

from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]
ImageUrl = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class OfferPackageCreate(ORMModel):
    service_id: int
    title: Title
    description: str | None = None
    image_url: ImageUrl
    original_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    offer_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    currency: str = "AED"
    status: RecordStatus = RecordStatus.active

    @model_validator(mode="after")
    def validate_prices(self):
        if self.offer_price >= self.original_price:
            raise ValueError("offer_price must be lower than original_price")
        return self


class OfferPackageUpdate(ORMModel):
    service_id: int | None = None
    title: Title | None = None
    description: str | None = None
    image_url: ImageUrl | None = None
    original_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    offer_price: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=2)
    currency: str | None = None
    status: RecordStatus | None = None

    @model_validator(mode="after")
    def reject_null_required_fields(self):
        for field in ("service_id", "title", "image_url", "original_price", "offer_price", "currency", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class OfferPackageRead(OfferPackageCreate, Timestamped):
    id: int
    discount_percentage: int
    service_name: str | None = None
    category_id: int | None = None
