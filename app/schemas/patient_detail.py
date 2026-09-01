from app.schemas.booking import BookingRead
from app.schemas.patient import PatientRead
from app.schemas.patient_document import PatientDocumentRead
from app.schemas.prescription import PrescriptionRead


class PatientDetail(PatientRead):
    bookings: list[BookingRead] = []
    prescriptions: list[PrescriptionRead] = []
    patient_documents: list[PatientDocumentRead] = []
