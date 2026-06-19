from app.schemas.common import ORMModel, Timestamped


class ContactCreate(ORMModel):
    full_name: str
    phone: str
    email: str | None = None
    message: str | None = None
    source: str = "walk_in"
    status: str = "new"
    notes: str | None = None


class ContactUpdate(ORMModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    message: str | None = None
    source: str | None = None
    status: str | None = None
    notes: str | None = None


class ContactRead(Timestamped):
    id: int
    full_name: str
    phone: str
    email: str | None
    message: str | None
    source: str
    status: str
    notes: str | None
