from app.schemas.common import ORMModel, Timestamped


class PatientDocumentCreate(ORMModel):
    title: str
    document_type: str | None = None
    file_name: str
    content_type: str | None = None
    external_url: str | None = None
    notes: str | None = None


class PatientDocumentUpdate(ORMModel):
    title: str | None = None
    document_type: str | None = None
    file_name: str | None = None
    content_type: str | None = None
    external_url: str | None = None
    notes: str | None = None


class PatientDocumentRead(Timestamped):
    id: int
    patient_id: int
    title: str
    document_type: str | None
    file_name: str
    content_type: str | None
    storage_key: str
    external_url: str | None
    notes: str | None
    uploaded_by_user_id: int | None
