from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import ClinicSetting
from app.schemas.setting import ClinicSettingsUpdate


DEFAULT_CLINIC_SETTINGS = {
    "clinic_name": "Royal Dutch Medical Centre",
    "clinic_email": "info@royaldutch.ae",
    "clinic_email_cc": "",
    "clinic_email_bcc": "",
    "clinic_phone": "+971 000 000 000",
    "clinic_address": "Dubai, United Arab Emirates",
    "invoice_footer": "Thank you for choosing Royal Dutch Medical Centre.",
    "invoice_terms": "Payment is due on receipt unless otherwise agreed by the clinic.",
    "tax_registration_number": "",
    "default_currency": "AED",
}


def get_clinic_settings(db: Session | None = None) -> dict[str, str]:
    settings = DEFAULT_CLINIC_SETTINGS.copy()
    if not db:
        return settings
    rows = db.scalars(select(ClinicSetting)).all()
    for row in rows:
        if row.key in settings and row.value is not None:
            settings[row.key] = row.value
    return settings


def seed_clinic_settings(db: Session) -> None:
    for key, value in DEFAULT_CLINIC_SETTINGS.items():
        exists = db.scalar(select(ClinicSetting).where(ClinicSetting.key == key))
        if not exists:
            db.add(ClinicSetting(key=key, value=value))
    db.commit()


def update_clinic_settings(db: Session, data: ClinicSettingsUpdate) -> dict[str, str]:
    values = data.model_dump(exclude_unset=True)
    for key, value in values.items():
        if key not in DEFAULT_CLINIC_SETTINGS:
            continue
        setting = db.scalar(select(ClinicSetting).where(ClinicSetting.key == key))
        if setting:
            setting.value = value
        else:
            db.add(ClinicSetting(key=key, value=value))
    db.commit()
    return get_clinic_settings(db)
