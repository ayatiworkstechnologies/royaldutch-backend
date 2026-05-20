from app.models.enums import RecordStatus
from app.schemas.common import ORMModel, Timestamped


class EmailTemplateBase(ORMModel):
    name: str
    slug: str
    description: str | None = None
    subject: str
    body: str
    status: RecordStatus = RecordStatus.active


class EmailTemplateCreate(EmailTemplateBase):
    pass


class EmailTemplateUpdate(ORMModel):
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    subject: str | None = None
    body: str | None = None
    status: RecordStatus | None = None


class EmailTemplateRead(EmailTemplateBase, Timestamped):
    id: int
