from app.schemas.common import ORMModel, Timestamped


class PatientBase(ORMModel):
    full_name: str
    email: str | None = None
    phone: str
    gender: str | None = None
    age: int | None = None
    notes: str | None = None
    documents: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(ORMModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    gender: str | None = None
    age: int | None = None
    notes: str | None = None
    documents: str | None = None


class PatientRead(PatientBase, Timestamped):
    id: int
