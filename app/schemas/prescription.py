from app.schemas.common import ORMModel, Timestamped


class PrescriptionCreate(ORMModel):
    drug_name: str
    dosage: str
    frequency: str
    duration: str
    notes: str | None = None


class PrescriptionUpdate(ORMModel):
    drug_name: str | None = None
    dosage: str | None = None
    frequency: str | None = None
    duration: str | None = None
    notes: str | None = None


class PrescriptionRead(Timestamped):
    id: int
    patient_id: int
    booking_id: int
    staff_id: int | None
    drug_name: str
    dosage: str
    frequency: str
    duration: str
    notes: str | None
