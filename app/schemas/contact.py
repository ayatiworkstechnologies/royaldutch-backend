from pydantic import field_validator, model_validator

from app.schemas.common import ORMModel, Timestamped
from app.services.smtp_service import EMAIL_PATTERN


class ContactCreate(ORMModel):
    full_name: str
    phone: str
    email: str | None = None
    message: str | None = None
    source: str = "walk_in"
    status: str = "new"
    notes: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        email = value.strip()
        if not EMAIL_PATTERN.fullmatch(email):
            raise ValueError("Enter a valid email address")
        return email

    @model_validator(mode="after")
    def require_website_email(self):
        if self.source == "website" and not self.email:
            raise ValueError("Email is required for website enquiries")
        return self


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
    email_triggered: bool = False
    management_email_status: str = "not_triggered"
    customer_email_status: str = "not_triggered"
