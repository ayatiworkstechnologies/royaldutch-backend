from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


class CategoryBase(ORMModel):
    external_id: int | None = None
    name: str
    slug: str
    description: str | None = None
    status: RecordStatus = RecordStatus.active


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(ORMModel):
    external_id: int | None = None
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    status: RecordStatus | None = None


class CategoryRead(CategoryBase, Timestamped):
    id: int
