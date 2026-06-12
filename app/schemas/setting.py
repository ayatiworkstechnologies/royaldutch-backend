from app.schemas.common import ORMModel


class ClinicSettingsRead(ORMModel):
    clinic_name: str
    clinic_email: str
    clinic_phone: str
    clinic_address: str
    invoice_footer: str
    invoice_terms: str
    tax_registration_number: str
    default_currency: str


class ClinicSettingsUpdate(ORMModel):
    clinic_name: str | None = None
    clinic_email: str | None = None
    clinic_phone: str | None = None
    clinic_address: str | None = None
    invoice_footer: str | None = None
    invoice_terms: str | None = None
    tax_registration_number: str | None = None
    default_currency: str | None = None
