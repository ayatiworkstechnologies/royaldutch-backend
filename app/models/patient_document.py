from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class PatientDocument(TimestampMixin, Base):
    __tablename__ = "patient_documents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    external_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    patient = relationship("Patient", back_populates="patient_documents")
